
// const settings
//

class TransactionTable {
    constructor() {
        this.transactionTable = document.getElementById('transactionTable');
        this.mainplot = document.getElementById('main-plot');


        this.now = new Date();
        this.now.setHours(this.now.getHours()+24);
        this.then = new Date(this.now);
        this.then.setMonth(this.now.getMonth() -6);
    }

    makePlot() {
    }


    async displayTransactions(crsid) {
        // Show the transactions
        this.transactionTable.style.display = 'block';
        this.transactionTable.innerHTML = "<thead><tr>\
            <th style='width:100%'>Date</th><th>Transaction</th><th>Debit</th></tr></thead>";

        this.transactionTable.innerHTML += '<tbody>'; 
        
        const response = await fetch(`/api/timeseries?crsid=${crsid}&include_debit`);
        const data = await response.json();
        const fragment = document.createDocumentFragment();

        data["table"]
            .slice()  // clone to avoid modifying original
            .reverse()
            .forEach(row => {
                const tr = document.createElement('tr');
                const debit = Math.abs(row[2] / 100).toFixed(2);
                const amountText = row[2] > 0 ? `(£${debit})` : `£${debit}`;

                tr.innerHTML = `
                    <td>${row[0]}</td>
                    <td>${row[1]}</td>
                    <td>${amountText}</td>
                    `;
                fragment.appendChild(tr);
            });

        this.transactionTable.appendChild(fragment);
    }
};


class CRSIDAutocomplete {
    constructor() {
        this.users = {};
        this.filteredUsers = [];
        this.selectedIndex = -1;
        this.isLoading = false;

        this.input = document.getElementById('crsidInput');
        this.dropdown = document.getElementById('autocompleteDropdown');
        this.checkButton = document.getElementById('checkButton');
        this.result = document.getElementById('result');

        this.table = new TransactionTable();

        this.init();
    }

    async init() {
        await this.loadUsers();
        this.bindEvents();

        let crsid = localStorage.getItem('crsid');
        if (crsid !== null) {
            this.input.value = crsid;
            this.hideDropdown();
        }
    }

    async loadUsers() {
        try {
            const response = await fetch('/api/listusers');
            const data = await response.json();

            if (data.success) {
                this.users = data.users;
                console.log(`Loaded ${Object.keys(this.users).length} users`);
            } else {
                console.error('Failed to load users');
            }
        } catch (error) {
            console.error('Error loading users:', error);
        }
    }

    bindEvents() {
        this.input.addEventListener('input', (e) => this.handleInput(e));
        this.input.addEventListener('keydown', (e) => this.handleKeydown(e));
        this.input.addEventListener('blur', (e) => this.handleBlur(e));
        this.input.addEventListener('focus', (e) => this.handleFocus(e));

        this.checkButton.addEventListener('click', () => this.checkBalance());

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.input.contains(e.target) && !this.dropdown.contains(e.target)) {
                this.hideDropdown();
            }
        });
    }

    handleInput(e) {
        const value = e.target.value.toLowerCase().trim();

        if (value.length === 0) {
            this.hideDropdown();
            return;
        }

        this.filterUsers(value);
        this.showDropdown();
        this.selectedIndex = -1;
    }

    handleKeydown(e) {
        if (!this.isDropdownVisible()) return;

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.selectNext();
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.selectPrevious();
                break;
            case 'Enter':
                e.preventDefault();
                if (this.selectedIndex >= 0) {
                    this.selectUser(this.filteredUsers[this.selectedIndex]);
                } else {
                    this.checkBalance();
                }
                break;
            case 'Escape':
                this.hideDropdown();
                break;
        }
    }

    handleBlur(e) {
        // Delay hiding to allow click events on dropdown items
        setTimeout(() => this.hideDropdown(), 150);
    }

    handleFocus(e) {
        if (this.input.value.trim().length > 0) {
            this.filterUsers(this.input.value.toLowerCase().trim());
            this.showDropdown();
        }
    }

    filterUsers(query) {
        this.filteredUsers = Object.keys(this.users)
            .filter(crsid => crsid.toLowerCase().includes(query))
            .sort()
            .slice(0, 10); // Limit to 10 results
    }

    showDropdown() {
        if (this.filteredUsers.length === 0) {
            this.hideDropdown();
            return;
        }

        this.dropdown.innerHTML = '';

        this.filteredUsers.forEach((crsid, index) => {
            const item = document.createElement('div');
            item.className = 'autocomplete-item';
            item.innerHTML = `
                <span>${crsid}</span>
                <span class="rfid-status ${this.users[crsid] ? 'rfid-yes' : 'rfid-no'}">
                ${this.users[crsid] ? 'Card Registered' : 'Unregistered'}
                </span>
                `;

            item.addEventListener('click', () => this.selectUser(crsid));
            this.dropdown.appendChild(item);
        });

        this.dropdown.style.display = 'block';
    }

    hideDropdown() {
        this.dropdown.style.display = 'none';
        this.selectedIndex = -1;
    }

    isDropdownVisible() {
        return this.dropdown.style.display === 'block';
    }

    selectNext() {
        this.selectedIndex = Math.min(this.selectedIndex + 1, this.filteredUsers.length - 1);
        this.updateSelection();
    }

    selectPrevious() {
        this.selectedIndex = Math.max(this.selectedIndex - 1, -1);
        this.updateSelection();
    }

    updateSelection() {
        const items = this.dropdown.querySelectorAll('.autocomplete-item');
        items.forEach((item, index) => {
            item.classList.toggle('selected', index === this.selectedIndex);
        });
    }

    selectUser(crsid) {
        this.input.value = crsid;
        this.hideDropdown();
        this.input.focus();
    }


    async checkBalance() {
        const crsid = this.input.value.trim().toLowerCase();

        if (!crsid) {
            this.showResult('Please enter a CRSID', 'error');
            return;
        }

        this.showResult('Checking balance...', 'loading');
        this.checkButton.disabled = true;
        localStorage.setItem('crsid', crsid);

        try {
            const response = await fetch(`/api/balance/${crsid}`);
            const data = await response.json();

            console.log(data);

            if (response.ok && data.success !== false) {
                const balance = -data.debt || 0;
                const balanceText = balance === 0 ? 'Zero balance' : 
                    balance < 0 ? `£${Math.abs(balance / 100).toFixed(2)} owed` :
                `£${(balance / 100).toFixed(2)} credit`;

                this.showResult(`Balance for ${crsid}: ${balanceText}`, 'success');
            } else {
                this.showResult(data.reason, 'error');
            }

            this.table.displayTransactions(crsid);

        } catch (error) {
            this.showResult('Error checking balance', 'error');
            console.error('Balance check error:', error);
        } finally {
            this.checkButton.disabled = false;
        }
    }

    showResult(message, type) {
        this.result.textContent = message;
        this.result.className = `result ${type}`;
        this.result.style.display = 'block';

        if (type === 'loading') {
            this.result.className = 'result loading';
        }
    }
}

// Initialize the autocomplete when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new CRSIDAutocomplete();
});
