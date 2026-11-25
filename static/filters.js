(() => {
    'use strict';
    const $ = (id) => document.getElementById(id);
    const dialog = $('filter-dialog');
    const form = $('filter-form');
    const field = (name) => form.elements.namedItem(name);
    const defaults = () => ({term:'', ada:'', protocol:'', type:'', tag:'', status:'published',
        issue_from:'', issue_to:'', updated_from:'', updated_to:'', include_supervised:false, extra:{}});
    const copy = {
        el: {title:'Φίλτρα αναζήτησης',search:'Αναζήτηση',more:'Περισσότερες επιλογές',termPlaceholder:'π.χ. προσλήψεις, προμήθεια εξοπλισμού',adaHelp:'Μοναδικός κωδικός απόφασης, π.χ. 9ΖΔΠ46ΨΧΗ5-Ζ16.',protocolHelp:'Συμπλήρωσέ τον μόνο αν γνωρίζεις τον αριθμό πρωτοκόλλου.',issueHelp:'Προαιρετικό. Συμπλήρωσε και τις δύο ημερομηνίες για συγκεκριμένο διάστημα έως 180 ημερών. Αλλιώς ισχύει το προεπιλεγμένο διάστημα της Διαύγειας.',term:'Λέξεις αναζήτησης',protocol:'Αριθμός πρωτοκόλλου',classification:'Κατηγοριοποίηση',type:'Είδος πράξης',theme:'Θεματική ενότητα',status:'Κατάσταση',published:'Αναρτημένες',revoked:'Ανακληθείσες',pending:'Σε αναμονή ανάκλησης',allStatuses:'Όλες οι καταστάσεις',dates:'Ημερομηνίες',dateHelp:'Το διάστημα έκδοσης περιορίζεται σε 180 ημερολογιακές ημέρες. Η τελευταία ενημέρωση είναι επιπλέον κριτήριο μέσα σε αυτό το διάστημα.',issueFrom:'Έκδοση από',issueTo:'Έκδοση έως',updatedFrom:'Ενημέρωση από',updatedTo:'Ενημέρωση έως',supervised:'Συμπερίληψη εποπτευόμενων φορέων',special:'Ειδικά κριτήρια είδους πράξης',specialHelp:'Εμφανίζονται τα διαθέσιμα πεδία της Διαύγειας για το επιλεγμένο είδος. Τα λεξικά φορτώνονται όταν ανοίγεις ένα πεδίο.',reset:'Καθαρισμός',cancel:'Ακύρωση',apply:'Εφαρμογή φίλτρων',retry:'Δοκιμή ξανά',all:'Όλα',loading:'Φόρτωση επιλογών…',error:'Δεν φορτώθηκαν οι επιλογές. Δοκίμασε ξανά.',dateError:'Δώσε πλήρες διάστημα έκδοσης έως 180 ημερολογιακών ημερών και έγκυρο διάστημα ενημέρωσης.',numberError:'Έλεγξε τα ελάχιστα και μέγιστα ποσά (έως 6 δεκαδικά ψηφία).',min:'Ελάχιστο',max:'Μέγιστο',yes:'Ναι',no:'Όχι',remove:'Αφαίρεση φίλτρου',clear:'Καθαρισμός φίλτρων',period:'Διάστημα έκδοσης',updated:'Διάστημα ενημέρωσης',recent:'Τελευταίες 180 ημέρες · πιο πρόσφατες ενημερώσεις πρώτα',dictionary:'Κωδικός από το λεξικό',close:'Κλείσιμο φίλτρων'},
        en: {title:'Search filters',search:'Search',more:'More options',termPlaceholder:'e.g. recruitment, equipment procurement',adaHelp:'Unique decision code, e.g. 9ΖΔΠ46ΨΧΗ5-Ζ16.',protocolHelp:'Only fill this in if you know the protocol number.',issueHelp:'Optional. Enter both dates for a specific period of up to 180 days. Otherwise Diavgeia uses its default period.',term:'Search words',protocol:'Protocol number',classification:'Classification',type:'Decision type',theme:'Thematic category',status:'Status',published:'Published',revoked:'Revoked',pending:'Pending revocation',allStatuses:'All statuses',dates:'Dates',dateHelp:'Issue dates are limited to 180 calendar days. Last updated dates are an additional restriction within that issue period.',issueFrom:'Issued from',issueTo:'Issued until',updatedFrom:'Updated from',updatedTo:'Updated until',supervised:'Include supervised organizations',special:'Decision-type-specific criteria',specialHelp:'Available fields come from Diavgeia for the chosen decision type. Dictionaries load when you focus a field.',reset:'Clear',cancel:'Cancel',apply:'Apply filters',retry:'Try again',all:'All',loading:'Loading options…',error:'Unable to load options. Please try again.',dateError:'Enter a complete issue period of up to 180 calendar days and a valid updated period.',numberError:'Check the minimum and maximum amounts (up to 6 decimal places).',min:'Minimum',max:'Maximum',yes:'Yes',no:'No',remove:'Remove filter',clear:'Clear filters',period:'Issue period',updated:'Updated period',recent:'Last 180 days · most recently updated first',dictionary:'Dictionary code',close:'Close filters'},
    };
    const t = (key) => copy[document.documentElement.lang === 'en' ? 'en' : 'el'][key];
    let applied = defaults();
    let draftExtra = {};
    let specialControls = new Map();
    let options = null;
    let optionsLoading = false;
    let specialSequence = 0;
    let specialState = 'idle';
    let optionsState = 'idle';
    const specialCache = new Map();
    const dictionaries = new Map();
    const clone = (value) => JSON.parse(JSON.stringify(value));
    function filterSignature(value) {
        const ordered = (item) => item && typeof item === 'object'
            ? Object.fromEntries(Object.keys(item).sort().map(key => [key, ordered(item[key])]))
            : item;
        return JSON.stringify(ordered(value));
    }
    function parameters() {
        const params = {};
        for (const [key,value] of Object.entries(applied)) {
            if (key === 'extra') { if (Object.keys(value).length) params.extra=JSON.stringify(value); }
            else if (value !== '' && value !== false) params[key]=String(value);
        }
        return params;
    }
    function notify() { renderSummary(); document.dispatchEvent(new CustomEvent('filters-applied')); }
    function renderSummary() {
        const chips = [];
        const label = (key) => ({ada:'ΑΔΑ / ADA',tag:t('theme'),include_supervised:t('supervised')})[key] || t(key) || key;
        for (const key of ['term','ada','protocol','type','tag']) {
            if (!applied[key]) continue;
            const item = key === 'type' ? options?.decisionTypes.find(x=>x.uid===applied[key]) : key === 'tag' ? options?.thematicCategories.find(x=>x.uid===applied[key]) : null;
            chips.push({label:`${label(key)}: ${item?.label || applied[key]}`,clear:()=>{applied[key]='';if(key==='type')applied.extra={};}});
        }
        if (applied.status!=='published') chips.push({label:t(applied.status==='all'?'allStatuses':applied.status==='revoked'?'revoked':'pending'),clear:()=>{applied.status='published';}});
        for (const prefix of ['issue','updated']) if (applied[`${prefix}_from`]) chips.push({label:`${t(prefix==='issue'?'period':'updated')}: ${applied[`${prefix}_from`]} – ${applied[`${prefix}_to`]}`,clear:()=>{applied[`${prefix}_from`]='';applied[`${prefix}_to`]='';}});
        if (applied.include_supervised) chips.push({label:t('supervised'),clear:()=>{applied.include_supervised=false;}});
        for(const [term,value] of Object.entries(applied.extra)) {
            const definition=specialCache.get(applied.type)?.fields.find(x=>x.term===term);
            const text=typeof value==='object'?`${value.min || '…'} – ${value.max || '…'}`:value;
            chips.push({label:`${definition?.label || term}: ${text}`,clear:()=>{delete applied.extra[term];}});
        }
        $('active-filters').replaceChildren();
        for(const chip of chips) {
            const button=document.createElement('button');button.type='button';button.className='filter-chip';
            button.textContent=chip.label+' ×';button.title=chip.label;button.setAttribute('aria-label',`${t('remove')}: ${chip.label}`);
            button.addEventListener('click',()=>{chip.clear();notify();});$('active-filters').append(button);
        }
        if(chips.length){const button=document.createElement('button');button.type='button';button.className='text-button';button.textContent=t('clear');button.addEventListener('click',()=>{applied=defaults();notify();});$('active-filters').append(button);}
        $('filter-count').hidden=!chips.length;$('filter-count').textContent=chips.length;
        $('search-period').textContent=applied.issue_from?`${t('period')}: ${applied.issue_from} – ${applied.issue_to}`:t('recent');
    }
    async function json(url) { const response=await fetch(url);if(!response.ok)throw new Error('upstream');return response.json(); }
    function status(id, state) { $(id).textContent=state==='loading'?t('loading'):state==='error'?t('error'):''; }
    function updateLanguage() {
        dialog.querySelectorAll('[data-filter-i18n]').forEach(el=>{el.textContent=t(el.dataset.filterI18n);});
        $('close-filters').setAttribute('aria-label',t('close'));
        field('term').placeholder = t('termPlaceholder');
        for(const id of ['modal-type','modal-theme']) if($(id).options[0])$(id).options[0].textContent=t('all');
        status('filter-options-status',optionsState);status('special-status',specialState);
        renderSummary();
    }
    function populate(select, rows) {
        const selected=select.value;select.replaceChildren(new Option(t('all'),''));
        rows.forEach(row=>select.add(new Option(row.label,row.uid)));select.value=selected;
    }
    async function loadOptions() {
        if(optionsLoading)return;
        optionsLoading=true;optionsState='loading';status('filter-options-status',optionsState);$('retry-filter-options').hidden=true;
        $('modal-type').disabled=$('modal-theme').disabled=true;
        try {
            if(!options)options=await json('/api/filters');
            populate($('modal-type'),options.decisionTypes);populate($('modal-theme'),options.thematicCategories);
            optionsState='ready';
        }catch(_){optionsState='error';}
        optionsLoading=false;status('filter-options-status',optionsState);$('retry-filter-options').hidden=optionsState!=='error';
        $('modal-type').disabled=$('modal-theme').disabled=optionsState!=='ready';
    }
    function rememberSpecial() {
        if(specialState!=='ready')return;
        draftExtra={};
        for(const [term,controls] of specialControls){
            if(controls.min){if(controls.min.value||controls.max.value)draftExtra[term]={min:controls.min.value,max:controls.max.value};}
            else if(controls.input.value.trim())draftExtra[term]=controls.input.value.trim();
        }
    }
    async function loadSpecial() {
        const type=field('type').value,seq=++specialSequence;
        specialControls=new Map();$('special-fields').replaceChildren();$('special-section').hidden=true;$('retry-special').hidden=true;
        if(!type){specialState='idle';status('special-status',specialState);return;}
        specialState='loading';status('special-status',specialState);
        try {
            if(!specialCache.has(type))specialCache.set(type,await json(`/api/special-filters?type=${encodeURIComponent(type)}`));
            if(seq!==specialSequence||!dialog.open)return;
            const fields=specialCache.get(type).fields;
            for(const definition of fields){
                const label=document.createElement('label');label.className='filter-field';
                const title=document.createElement('span');title.textContent=definition.label;label.append(title);
                if(definition.type==='number'){
                    const group=document.createElement('span');group.className='numeric-range';
                    const inputs={};
                    for(const key of ['min','max']){const input=document.createElement('input');input.type='number';input.step='any';input.placeholder=t(key);input.setAttribute('aria-label',`${definition.label}: ${t(key)}`);input.value=draftExtra[definition.term]?.[key]||'';inputs[key]=input;group.append(input);}
                    specialControls.set(definition.term,inputs);label.append(group);
                }else{
                    const input=definition.type==='boolean'||definition.options.length?document.createElement('select'):document.createElement('input');
                    if(input.tagName==='SELECT'){
                        input.add(new Option(t('all'),''));
                        const choices=definition.type==='boolean'?[{value:'true',label:t('yes')},{value:'false',label:t('no')}]:definition.options.map(value=>({value,label:value}));
                        choices.forEach(item=>input.add(new Option(item.label,item.value)));
                    }else{input.maxLength=300;}
                    input.value=draftExtra[definition.term]||'';specialControls.set(definition.term,{input});label.append(input);
                    if(definition.dictionary){
                        const list=document.createElement('datalist');list.id=`extra-${definition.term}`;input.setAttribute('list',list.id);input.placeholder=t('dictionary');label.append(list);
                        input.addEventListener('focus',async()=>{
                            if(list.children.length)return;
                            try{if(!dictionaries.has(definition.dictionary))dictionaries.set(definition.dictionary,await json(`/api/filter-dictionary?name=${encodeURIComponent(definition.dictionary)}`));
                                for(const item of dictionaries.get(definition.dictionary).items){const option=document.createElement('option');option.value=item.uid;option.label=item.label;list.append(option);}}
                            catch(_){input.placeholder=t('dictionary');}
                        });
                    }
                }
                $('special-fields').append(label);
            }
            $('special-section').hidden=!fields.length;specialState='ready';
        }catch(_){if(seq!==specialSequence)return;specialState='error';}
        status('special-status',specialState);$('retry-special').hidden=specialState!=='error';
    }
    function fill(values) {
        form.reset();
        $('more-filter-options').open = false;
        for(const [key,value] of Object.entries(values)){
            if(key==='extra')continue;
            const control=field(key);if(!control)continue;
            if(key==='include_supervised')control.checked=value;else control.value=value;
        }
        draftExtra=clone(values.extra);$('filter-error').hidden=true;
    }
    function showError(message){$('filter-error').hidden=false;$('filter-error').textContent=message;$('filter-error').scrollIntoView({block:'nearest'});}
    form.addEventListener('submit',(event)=>{
        event.preventDefault();rememberSpecial();const next=defaults();
        for(const key of Object.keys(next)){if(key==='extra')continue;next[key]=key==='include_supervised'?field(key).checked:field(key).value.trim();}
        const from=next.issue_from,to=next.issue_to,days=(Date.parse(to)-Date.parse(from))/86400000;
        if(!!from!==!!to||((from||to)&&(!Number.isFinite(days)||days<0||days>179))||!!next.updated_from!==!!next.updated_to||(next.updated_from&&next.updated_from>next.updated_to)){showError(t('dateError'));return;}
        if(Object.keys(draftExtra).length&&specialState!=='ready'){showError(t('error'));return;}
        for(const value of Object.values(draftExtra))if(typeof value==='object'){
            const pattern=/^-?\d{1,16}(?:\.\d{1,6})?$/;
            if((value.min&&!pattern.test(value.min))||(value.max&&!pattern.test(value.max))||(value.min&&value.max&&Number(value.min)>Number(value.max))){showError(t('numberError'));return;}
        }
        next.extra=clone(draftExtra);
        if (filterSignature(next) === filterSignature(applied)) {
            dialog.close();
            return;
        }
        applied=next;dialog.close();notify();
    });
    $('modal-type').addEventListener('change',()=>{draftExtra={};loadSpecial();});
    $('reset-filter-draft').addEventListener('click',()=>{fill(defaults());loadSpecial();});
    $('close-filters').addEventListener('click',()=>dialog.close());$('cancel-filters').addEventListener('click',()=>dialog.close());
    $('retry-filter-options').addEventListener('click',loadOptions);$('retry-special').addEventListener('click',loadSpecial);
    dialog.addEventListener('close',()=>{specialSequence++;document.body.classList.remove('filters-open');$('open-filters').focus({preventScroll:true});});
    window.searchFilters={parameters,renderSummary,updateLanguage,
        statusLabel(value){return value==='REVOKED'?t('revoked'):value==='PENDING_REVOCATION'?t('pending'):'';},
        open(id){if(!id)return;updateLanguage();fill(applied);$('filter-organization').textContent=$('selected-title').textContent;dialog.showModal();document.body.classList.add('filters-open');loadOptions().then(()=>{if(dialog.open){field('type').value=applied.type;field('tag').value=applied.tag;loadSpecial();}});}
    };
})();
