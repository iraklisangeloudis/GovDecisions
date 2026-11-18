(() => {
    'use strict';

    const $ = (id) => document.getElementById(id);
    const copy = {
        el: {
            filtersButton: 'Φίλτρα',
            brand: 'Δημόσιες αποφάσεις', tagline: 'Αναρτήσεις από τη Διαύγεια', skip: 'Στο περιεχόμενο',
            ministries: 'Υπουργεία', chooseOne: 'Επίλεξε έναν φορέα', loadingMinistries: 'Φόρτωση υπουργείων…',
            retry: 'Δοκιμή ξανά', source: 'Πηγή δεδομένων: Διαύγεια', browse: 'ΠΕΡΙΗΓΗΣΗ ΣΤΙΣ ΑΠΟΦΑΣΕΙΣ',
            welcomeTitle: 'Οι δημόσιες αποφάσεις, σε ένα σημείο.', welcomeText: 'Επίλεξε έναν φορέα για να δεις τις αποφάσεις του.',
            chooseMinistry: 'Επιλογή φορέα →', officialContent: 'Οι τίτλοι και τα έγγραφα διατηρούν την επίσημη γλώσσα τους.',
            recentDecisions: 'ΠΡΟΣΦΑΤΕΣ ΑΠΟΦΑΣΕΙΣ', clear: 'Καθαρισμός επιλογής',
            supervised: 'Συμπερίληψη εποπτευόμενων φορέων', dateRange: 'Τελευταίες 180 ημέρες · πιο πρόσφατες ενημερώσεις πρώτα',
            stale: 'Η Διαύγεια δεν είναι διαθέσιμη. Εμφανίζονται προηγούμενα αποτελέσματα.',
            loading: 'Φόρτωση αποφάσεων…', empty: 'Δεν βρέθηκαν αποφάσεις για αυτόν τον φορέα.',
            error: 'Δεν ήταν δυνατή η φόρτωση. Δοκίμασε ξανά.', end: 'Έφτασες στο τέλος των αποτελεσμάτων.',
            more: 'Περισσότερες αποφάσεις', issued: 'Έκδοση', updated: 'Ενημέρωση', ada: 'ΑΔΑ', pdf: 'Άνοιγμα PDF ↗',
            shown: (n, total) => `${n} από ${total} αποφάσεις`, openMenu: 'Άνοιγμα μενού φορέων', closeMenu: 'Κλείσιμο μενού φορέων',
            lightTheme: 'Ανοιχτό θέμα', darkTheme: 'Σκούρο θέμα', noMinistries: 'Δεν βρέθηκαν διαθέσιμα υπουργεία.',
            catalogStale: 'Εμφανίζεται προηγούμενος κατάλογος φορέων.',
            preview: 'Προεπισκόπηση PDF', download: 'Λήψη PDF', newTab: 'Άνοιγμα σε νέα καρτέλα', closePreview: 'Κλείσιμο προεπισκόπησης',
            pdfLoading: 'Φόρτωση PDF…', pdfError: 'Δεν ήταν δυνατή η προεπισκόπηση. Δοκίμασε ξανά ή κατέβασε το PDF.',
            pdfTooLarge: 'Το PDF είναι πολύ μεγάλο για προεπισκόπηση. Μπορείς να το κατεβάσεις.',
            pdfHelp: 'Αν δεν εμφανίζεται η προεπισκόπηση, άνοιξε το PDF σε νέα καρτέλα ή κατέβασέ το.',
        },
        en: {
            filtersButton: 'Filters',
            brand: 'Public decisions', tagline: 'Publications from Diavgeia', skip: 'Skip to content',
            ministries: 'Ministries', chooseOne: 'Select an organization', loadingMinistries: 'Loading ministries…',
            retry: 'Try again', source: 'Data source: Diavgeia', browse: 'BROWSE PUBLIC DECISIONS',
            welcomeTitle: 'Public decisions, in one place.', welcomeText: 'Select an organization to browse its decisions.',
            chooseMinistry: 'Choose an organization →', officialContent: 'Titles and documents remain in their official language.',
            recentDecisions: 'RECENT DECISIONS', clear: 'Clear selection', supervised: 'Include supervised organizations',
            dateRange: 'Last 180 days · most recently updated first',
            stale: 'Diavgeia is unavailable. Showing previously fetched results.',
            loading: 'Loading decisions…', empty: 'No decisions found for this organization.',
            error: 'Unable to load results. Please try again.', end: 'You have reached the end of the results.',
            more: 'More decisions', issued: 'Issued', updated: 'Updated', ada: 'ADA', pdf: 'Open PDF ↗',
            shown: (n, total) => `${n} of ${total} decisions`, openMenu: 'Open organization menu', closeMenu: 'Close organization menu',
            lightTheme: 'Light theme', darkTheme: 'Dark theme', noMinistries: 'No ministries available.',
            catalogStale: 'Showing a previously fetched organization list.',
            preview: 'PDF preview', download: 'Download PDF', newTab: 'Open in new tab', closePreview: 'Close preview',
            pdfLoading: 'Loading PDF…', pdfError: 'Unable to preview this PDF. Try again or download it.',
            pdfTooLarge: 'This PDF is too large to preview. You can download it instead.',
            pdfHelp: 'If the preview does not display, open the PDF in a new tab or download it.',
        },
    };
    const stored = (key) => { try { return localStorage.getItem(key); } catch (_) { return null; } };
    const persist = (key, value) => { try { localStorage.setItem(key, value); } catch (_) {} };
    let language = stored('decisions-language') === 'en' ? 'en' : 'el';
    let organizations = [];
    let catalogState = 'loading';
    let selected = null;
    let controller = null;
    let pendingState = null;
    const views = new Map();
    const mobile = matchMedia('(max-width: 760px)');
    let sidebarOpen = !mobile.matches;
    const t = (key) => copy[language][key];
    const viewKey = () => JSON.stringify([selected, window.searchFilters.parameters()]);
    const current = () => selected ? views.get(viewKey()) : null;
    const number = (value) => new Intl.NumberFormat(language === 'el' ? 'el-GR' : 'en-GB').format(value);
    const observer = 'IntersectionObserver' in window ? new IntersectionObserver((entries) => {
        const state = current();
        if (!$('pdf-dialog').open && !$('filter-dialog').open && entries.some((entry) => entry.isIntersecting) && state && state.loaded && state.more && !state.loading && !state.error) loadMore();
    }, { rootMargin: '0px 0px 240px 0px' }) : null;

    function setSidebar(open, focusFirst = false) {
        sidebarOpen = open;
        $('sidebar').hidden = !open;
        $('app-layout').classList.toggle('sidebar-hidden', !open);
        $('sidebar-backdrop').hidden = !mobile.matches || !open;
        document.body.classList.toggle('drawer-open', mobile.matches && open);
        $('main-content').inert = mobile.matches && open;
        $('menu-toggle').setAttribute('aria-expanded', String(open));
        $('menu-toggle').setAttribute('aria-label', t(open ? 'closeMenu' : 'openMenu'));
        if (focusFirst && open) $('organization-list').querySelector('button')?.focus();
    }

    function updateChrome() {
        document.documentElement.lang = language;
        document.title = t('brand');
        document.querySelectorAll('[data-i18n]').forEach((element) => { element.textContent = t(element.dataset.i18n); });
        $('lang-el').classList.toggle('current-language', language === 'el');
        $('lang-en').classList.toggle('current-language', language === 'en');
        $('language-toggle').setAttribute('aria-label', language === 'el' ? 'Switch to English' : 'Αλλαγή σε Ελληνικά');
        $('organization-list').setAttribute('aria-label', t('ministries'));
        $('sidebar-backdrop').setAttribute('aria-label', t('closeMenu'));
        document.querySelector('.brand').setAttribute('aria-label', t('brand'));
        const dark = document.documentElement.dataset.theme === 'dark';
        $('theme-icon').textContent = dark ? '☀' : '☾';
        $('theme-toggle').setAttribute('aria-label', t(dark ? 'lightTheme' : 'darkTheme'));
        setSidebar(sidebarOpen);
        renderCatalogStatus();
        window.searchFilters.updateLanguage();
        window.pdfPreview.updateLanguage(t);
    }

    function renderCatalogStatus() {
        const message = { loading: 'loadingMinistries', error: 'error', empty: 'noMinistries', stale: 'catalogStale' }[catalogState];
        $('organizations-status').hidden = !message;
        $('organizations-status').classList.toggle('is-loading', catalogState === 'loading');
        $('organizations-status').textContent = message ? t(message) : '';
        $('organizations-retry').hidden = catalogState !== 'error';
    }

    async function loadOrganizations() {
        catalogState = 'loading';
        renderCatalogStatus();
        try {
            const response = await fetch('/api/organizations');
            if (!response.ok) throw new Error('upstream');
            const data = await response.json();
            if (!Array.isArray(data.organizations)) throw new Error('invalid response');
            organizations = data.organizations;
            $('organization-list').replaceChildren();
            organizations.forEach((organization) => {
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'organization-button';
                button.dataset.org = organization.uid;
                button.textContent = organization.label;
                button.setAttribute('aria-pressed', 'false');
                button.addEventListener('click', () => selectOrganization(organization.uid));
                $('organization-list').append(button);
            });
            catalogState = !organizations.length ? 'empty' : data.stale ? 'stale' : 'ready';
        } catch (_) { catalogState = 'error'; }
        renderCatalogStatus();
    }

    function abortPending() {
        if (pendingState) pendingState.loading = false;
        controller?.abort();
        controller = null;
        pendingState = null;
    }

    function selectOrganization(id) {
        const previous = current();
        if (previous) previous.scroll = window.scrollY;
        abortPending();
        selected = id === selected ? null : id;
        if (selected) {
            const key = viewKey();
            if (!views.has(key)) views.set(key, { rows: [], nextPage: 0, total: 0, more: true, loaded: false, loading: false, error: false, stale: false, scroll: 0 });
            else { const saved = views.get(key); views.delete(key); views.set(key, saved); }
            while (views.size > 8) views.delete(views.keys().next().value);
        }
        render();
        if (mobile.matches) setSidebar(false);
        window.scrollTo({ top: current()?.scroll || 0, behavior: 'instant' });
        if (selected && !current().loaded) loadMore();
        if (!sidebarOpen) $('main-content').focus({ preventScroll: true });
    }

    function timestamp(value, dateOnly = false) {
        if (typeof value !== 'number' || !Number.isFinite(value)) return '—';
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return '—';
        return new Intl.DateTimeFormat(language === 'el' ? 'el-GR' : 'en-GB', {
            dateStyle: 'short', ...(dateOnly ? {} : { timeStyle: 'short' }), timeZone: 'Europe/Athens',
        }).format(date);
    }

    function textElement(tag, className, text) {
        const element = document.createElement(tag);
        element.className = className;
        element.textContent = text;
        return element;
    }

    function renderCard(row) {
        const card = document.createElement('article');
        card.className = 'decision-card';
        if (row.organizationId !== selected) {
            card.append(textElement('p', 'decision-organization', row.organizationLabel));
        }
        const status = window.searchFilters.statusLabel(row.status);
        if (status) card.append(textElement('p', 'decision-status', status));
        card.append(textElement('h2', '', row.subject));
        const footer = textElement('div', 'decision-footer', '');
        const meta = textElement('div', 'decision-meta', '');
        meta.append(textElement('span', '', `${t('issued')}: ${timestamp(row.issueDate, true)}`));
        meta.append(textElement('span', '', `${t('updated')}: ${timestamp(row.submissionTimestamp)}`));
        meta.append(textElement('span', 'decision-ada', `${t('ada')}: ${row.ada}`));
        const pdf = textElement('button', 'pdf-link', t('preview'));
        pdf.type = 'button';
        pdf.addEventListener('click', () => window.pdfPreview.open(row, t));
        footer.append(meta, pdf);
        card.append(footer);
        return card;
    }

    function render() {
        observer?.disconnect();
        const state = current();
        document.querySelectorAll('.organization-button').forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.org === selected)));
        $('welcome-state').hidden = !!selected;
        $('decision-view').hidden = !selected;
        if (!state) { $('decision-list').replaceChildren(); return; }
        $('selected-title').textContent = organizations.find((org) => org.uid === selected)?.label || '';
        window.searchFilters.renderSummary();
        $('decision-list').replaceChildren(...state.rows.map(renderCard));
        $('decision-list').setAttribute('aria-busy', String(state.loading));
        $('stale-notice').hidden = !state.stale;
        $('results-summary').textContent = state.loaded ? t('shown')(number(state.rows.length), number(state.total)) : '';
        let message = '';
        if (state.loading) message = t('loading');
        else if (state.error) message = t('error');
        else if (state.loaded && !state.rows.length) message = t('empty');
        else if (state.loaded && !state.more) message = t('end');
        $('list-status').textContent = message;
        $('list-status').classList.toggle('error', state.error);
        $('load-more').hidden = state.loading || (!state.error && !state.more);
        $('load-more').textContent = t(state.error ? 'retry' : 'more');
        if (state.loaded && state.more && !state.loading && !state.error) observer?.observe($('scroll-sentinel'));
    }

    async function loadMore() {
        const state = current();
        if (!state || state.loading || !state.more) return;
        const requestController = new AbortController();
        controller = requestController;
        pendingState = state;
        state.loading = true;
        state.error = false;
        render();
        const query = new URLSearchParams({ org: selected, page: state.nextPage, size: 20, ...window.searchFilters.parameters() });
        try {
            const response = await fetch(`/api/decisions?${query}`, { signal: requestController.signal });
            if (!response.ok) throw new Error('upstream');
            const data = await response.json();
            if (controller !== requestController) return;
            if (!Array.isArray(data.decisions) || typeof data.hasMore !== 'boolean') throw new Error('invalid response');
            const seen = new Set(state.rows.map((row) => row.ada));
            data.decisions.forEach((row) => { if (!seen.has(row.ada)) { seen.add(row.ada); state.rows.push(row); } });
            state.total = data.total;
            state.more = data.hasMore;
            state.nextPage += 1;
            state.loaded = true;
            state.stale = state.stale || data.stale;
        } catch (error) {
            if (error.name !== 'AbortError' && controller === requestController) state.error = true;
        } finally {
            if (controller === requestController) {
                controller = null;
                pendingState = null;
                state.loading = false;
                render();
            }
        }
    }

    $('menu-toggle').addEventListener('click', () => setSidebar(!sidebarOpen));
    $('choose-ministry').addEventListener('click', () => setSidebar(true, true));
    $('sidebar-backdrop').addEventListener('click', () => { setSidebar(false); $('menu-toggle').focus(); });
    $('clear-selection').addEventListener('click', () => selectOrganization(selected));
    $('organizations-retry').addEventListener('click', loadOrganizations);
    $('load-more').addEventListener('click', loadMore);
    $('open-filters').addEventListener('click', () => window.searchFilters.open(selected));
    document.addEventListener('filters-applied', () => {
        if (!selected) return;
        const id = selected;
        abortPending();
        views.delete(viewKey());
        selected = null;
        selectOrganization(id);
    });
    $('language-toggle').addEventListener('click', () => {
        language = language === 'el' ? 'en' : 'el';
        persist('decisions-language', language);
        updateChrome();
        render();
    });
    $('theme-toggle').addEventListener('click', () => {
        document.documentElement.dataset.theme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
        persist('decisions-theme', document.documentElement.dataset.theme);
        updateChrome();
    });
    matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (event) => {
        if (!stored('decisions-theme')) { document.documentElement.dataset.theme = event.matches ? 'dark' : 'light'; updateChrome(); }
    });
    mobile.addEventListener('change', () => setSidebar(!mobile.matches));
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && sidebarOpen && !$('pdf-dialog').open && !$('filter-dialog').open) { setSidebar(false); $('menu-toggle').focus(); }
    });
    updateChrome();
    render();
    loadOrganizations();
})();
