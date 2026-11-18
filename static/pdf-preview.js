(() => {
    'use strict';
    const dialog = document.getElementById('pdf-dialog');
    const stage = document.getElementById('pdf-stage');
    const status = document.getElementById('pdf-status');
    const download = document.getElementById('pdf-download');
    const newTab = document.getElementById('pdf-new-tab');
    const retry = document.getElementById('pdf-retry');
    let row = null;
    let controller = null;
    let objectUrl = null;
    let translate = (key) => key;
    let statusKey = '';
    let previousFocus = null;

    function updateLanguage(t) {
        translate = t;
        document.getElementById('pdf-close').setAttribute('aria-label', t('closePreview'));
        status.textContent = statusKey ? t(statusKey) : '';
        const viewer = stage.querySelector('object');
        if (viewer) viewer.setAttribute('aria-label', `${t('preview')}: ${row.subject}`);
    }

    function release() {
        controller?.abort();
        controller = null;
        stage.replaceChildren();
        if (objectUrl) URL.revokeObjectURL(objectUrl);
        objectUrl = null;
    }

    async function load() {
        release();
        const pending = new AbortController();
        controller = pending;
        statusKey = 'pdfLoading';
        status.textContent = translate(statusKey);
        retry.hidden = true;
        const encoded = encodeURIComponent(row.ada);
        download.href = `/download/${encoded}`;
        download.download = `${row.ada}.pdf`;
        newTab.href = `/document/${encoded}`;
        try {
            const response = await fetch(`/document/${encoded}`, { signal: pending.signal });
            if (!response.ok) {
                const error = new Error('PDF request failed');
                error.tooLarge = response.status === 413;
                throw error;
            }
            const blob = await response.blob();
            if (controller !== pending || !dialog.open) return;
            if (blob.type.split(';')[0] !== 'application/pdf') throw new Error('Invalid PDF');
            objectUrl = URL.createObjectURL(blob);
            const viewer = document.createElement('object');
            viewer.type = 'application/pdf';
            viewer.data = objectUrl;
            viewer.setAttribute('aria-label', `${translate('preview')}: ${row.subject}`);
            const fallback = document.createElement('a');
            fallback.href = objectUrl;
            fallback.download = `${row.ada}.pdf`;
            fallback.textContent = translate('download');
            viewer.append(fallback);
            stage.replaceChildren(viewer);
            // Reuse the fetched bytes for downloads rather than fetching the PDF again.
            download.href = objectUrl;
            newTab.href = objectUrl;
            statusKey = '';
            status.textContent = '';
        } catch (error) {
            if (controller !== pending || error.name === 'AbortError') return;
            statusKey = error.tooLarge ? 'pdfTooLarge' : 'pdfError';
            status.textContent = translate(statusKey);
            retry.hidden = !!error.tooLarge;
        } finally {
            if (controller === pending) controller = null;
        }
    }

    document.getElementById('pdf-close').addEventListener('click', () => dialog.close());
    retry.addEventListener('click', load);
    dialog.addEventListener('click', (event) => {
        if (event.target !== dialog) return;
        const bounds = dialog.getBoundingClientRect();
        if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
    });
    dialog.addEventListener('close', () => {
        release();
        row = null;
        document.body.classList.remove('pdf-open');
        if (previousFocus?.isConnected) previousFocus.focus({ preventScroll: true });
        else document.getElementById('main-content').focus({ preventScroll: true });
    });
    window.pdfPreview = {
        updateLanguage,
        open(decision, t) {
            row = decision;
            previousFocus = document.activeElement;
            document.getElementById('pdf-title').textContent = decision.subject;
            updateLanguage(t);
            if (!dialog.open) dialog.showModal();
            document.body.classList.add('pdf-open');
            load();
        },
    };
})();
