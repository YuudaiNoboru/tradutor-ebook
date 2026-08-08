// Tab switching
function showTab(tabId) {
    document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
    document.querySelectorAll('.menu-item button').forEach(btn => btn.classList.remove('active'));

    document.getElementById(tabId).classList.add('active');

    const activeBtn = Array.from(document.querySelectorAll('.menu-item button')).find(btn => {
        const clickAttr = btn.getAttribute('onclick');
        return clickAttr && clickAttr.includes(tabId);
    });
    if (activeBtn) activeBtn.classList.add('active');

    if (window.innerWidth <= 1024) {
        document.getElementById('sidebarContainer').classList.remove('open');
    }
}

function toggleSidebarMobile() {
    document.getElementById('sidebarContainer').classList.toggle('open');
}

function toggleSidebarDesktop() {
    document.getElementById('appContainer').classList.toggle('collapsed');
}

// Filtro da tabela Ator/Ação. Funciona para qualquer número de atores:
// cada botão de filtro traz data-actor="<slug-do-papel>" (ex: "comprador",
// "estoquista", "sistema", "desenvolvedor") e cada linha da tabela traz
// data-actor-type com o mesmo slug. Não há mais uma lista fixa de 3 atores.
function filterTable() {
    const input = document.getElementById('searchInput');
    const filter = input.value.toLowerCase();
    const table = document.getElementById('mainTable');
    const tr = table.getElementsByTagName('tr');

    const activeActorBtn = document.querySelector('.filter-btn.active');
    const actorFilter = activeActorBtn ? activeActorBtn.getAttribute('data-actor') : 'todos';

    for (let i = 1; i < tr.length; i++) {
        const trElement = tr[i];
        const actorType = trElement.getAttribute('data-actor-type') || '';

        let textMatch = false;
        const tdList = trElement.getElementsByTagName('td');
        for (let j = 0; j < tdList.length; j++) {
            if (tdList[j]) {
                const txtValue = tdList[j].textContent || tdList[j].innerText;
                if (txtValue.toLowerCase().indexOf(filter) > -1) {
                    textMatch = true;
                    break;
                }
            }
        }

        const actorMatch = (actorFilter === 'todos' || actorType === actorFilter);

        trElement.style.display = (textMatch && actorMatch) ? "" : "none";
    }
}

function filterFileTable() {
    const input = document.getElementById('fileSearchInput');
    const filter = input.value.toLowerCase();
    const table = document.getElementById('fileTable');
    const tr = table.getElementsByTagName('tr');

    for (let i = 1; i < tr.length; i++) {
        const trElement = tr[i];
        let textMatch = false;
        const tdList = trElement.getElementsByTagName('td');

        for (let j = 0; j < tdList.length; j++) {
            if (tdList[j]) {
                const txtValue = tdList[j].textContent || tdList[j].innerText;
                if (txtValue.toLowerCase().indexOf(filter) > -1) {
                    textMatch = true;
                    break;
                }
            }
        }

        trElement.style.display = textMatch ? "" : "none";
    }
}

function filterActor(actor) {
    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
    const activeBtn = document.querySelector(`.filter-btn[data-actor="${actor}"]`);
    if (activeBtn) activeBtn.classList.add('active');
    filterTable();
}

// Seletor de diagrama de acoplamento por processo
function selectProcess(processId) {
    document.querySelectorAll('.proc-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById('btn-proc-' + processId).classList.add('active');
    document.querySelectorAll('.process-svg').forEach(svg => svg.classList.remove('active'));
    document.getElementById('proc-svg-' + processId).classList.add('active');
}

// Destaque de caminhos no diagrama Ator/Ação (Figura 1). Genérico para
// qualquer slug de ator: cada ator no SVG usa class="act-path path-<slug>"
// e existe um cartão de info correspondente com id="info-<slug>". Não há
// mais um "if" fixo para user/system/dev — qualquer papel novo funciona
// automaticamente desde que siga essa convenção de nomes.
function highlightPaths(actorKey) {
    document.querySelectorAll('.info-card').forEach(card => card.classList.remove('active'));

    document.querySelectorAll('.act-path').forEach(path => {
        path.setAttribute('opacity', '0.15');
        const pathConnector = path.querySelector('.connector');
        if (pathConnector) {
            pathConnector.classList.remove('active');
            pathConnector.style.stroke = '#64748b';
        }
    });

    document.querySelectorAll('.comp-node rect').forEach(rect => {
        rect.style.stroke = '#34d399';
        rect.style.strokeWidth = '1.5';
    });

    const activeColor = getComputedStyle(document.documentElement)
        .getPropertyValue(`--actor-color-${actorKey}`).trim() || '#38bdf8';

    document.querySelectorAll(`.path-${actorKey}`).forEach(path => {
        path.setAttribute('opacity', '1');
        const connector = path.querySelector('.connector');
        if (connector) {
            connector.classList.add('active');
            connector.style.stroke = activeColor;
        }
    });

    const infoCard = document.getElementById(`info-${actorKey}`);
    if (infoCard) infoCard.classList.add('active');

    // Componentes-alvo ficam destacados via atributo data-highlight-for
    // presente no próprio SVG gerado pela IA para este ator (ex:
    // data-highlight-for="comprador,sistema"), evitando um bloco de
    // if/else por ator como no template original.
    document.querySelectorAll(`[data-highlight-for~="${actorKey}"] rect`).forEach(rect => {
        rect.style.stroke = activeColor;
        rect.style.strokeWidth = '2.5';
    });
}
