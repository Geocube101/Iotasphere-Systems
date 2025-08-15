{
    function propagate_game_info(game_info)
    {
        let game_master = document.getElementById('gameextras');
        let navbar = document.getElementById('section-links');

        for (let game_index in game_info)
        {
            let game = game_info[game_index];
            let game_name = game['display-name'];
            let game_url = game['game-url'];
            let icon_image = game['icon-image'];
            let bg_image = game['background-image'];
            let sections = game['sections'];

            let section_container = document.createElement('div');
            let header_container = document.createElement('div');
            let header_container_child = document.createElement('div');
            let header = document.createElement('h1');
            let icon_img = document.createElement('img');
            let subsection_container = document.createElement('div');
            let background_image_box = document.createElement('div');
            let background_image = document.createElement('img');

            section_container.id = `game-${game_index}`;
            section_container.className = 'section-container';
            subsection_container.className = 'subsection-container';
            header.innerText = game_name;
            header.title = game_url;
            header.onclick = (e) => window.open(game_url, '_blank');
            header_container.className = 'section-header';
            if (icon_image !== null) icon_img.src = `/image/icon/${icon_image}`;
            icon_img.onclick = header.onclick;
            icon_img.title = header.title;
            if (bg_image !== null) background_image.src = `/image/background/${bg_image}`;
            background_image_box.className = 'background-image-box';

            for (let section of Object.values(sections))
            {
                if (!section['visible']) continue;
                let display_name = section['display-name'];

                let column = document.createElement('div');
                column.className = 'subsection';

                let col_header = document.createElement('h2');
                col_header.innerText = display_name;
                column.appendChild(col_header);

                for (let child of Object.values(section['children']))
                {
                    if (!child['visible']) continue;
                    let url = child['url'];
                    let child_icon_image = child['icon-image'];
                    let child_div = document.createElement('div');
                    let child_display_name = child['display-name'];
                    child_div.className = 'subsection-child';

                    let child_icon_img = document.createElement('img');
                    child_icon_img.className = 'game-icon-image';
                    child_icon_img.src = (child_icon_image === null) ? icon_img.src : `/image/icon/${child_icon_image}`;

                    let child_name = document.createElement('a');
                    child_name.className = 'game-name';
                    child_name.innerText = child_display_name;
                    child_name.href = url;
                    child_name.target = '_blank';

                    let domain_img = document.createElement('img')
                    domain_img.className = 'game-domain-icon-image';
                    domain_img.src = `https://s2.googleusercontent.com/s2/favicons?domain_url=${url}`;

                    if (child_display_name === null && url === null) child_name.title = 'N/A';
                    else if (child_display_name === null) child_name.title = url;
                    else if (url === null) child_name.title = child_display_name;
                    else child_name.title = `${child_display_name}\n${url}`;

                    child_div.appendChild(child_icon_img);
                    child_div.appendChild(child_name);
                    child_div.appendChild(domain_img);
                    column.appendChild(child_div);
                }

                subsection_container.appendChild(column);
            }

            background_image_box.appendChild(background_image);
            section_container.appendChild(background_image_box);
            header_container_child.appendChild(icon_img);
            header_container_child.appendChild(header);
            header_container.appendChild(header_container_child);
            section_container.appendChild(header_container);
            section_container.appendChild(subsection_container);
            game_master.appendChild(section_container);

            let anchor = document.createElement('a');
            anchor.innerText = game_name;
            anchor.href = `#${section_container.id}`;
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                document.querySelector(this.getAttribute('href')).scrollIntoView({behavior: 'smooth'});
            });
            navbar.appendChild(anchor);
        }
    }

    function propagate_program_info(program_info)
    {
        let program_master = document.getElementById('program-container');//2911
        let style = window.getComputedStyle(document.getElementById('program-container'));
        let program_colors = ['#EEEEEE', '#EB4034', '#C634EB', '#34EB62', '#EB9334'];
        let programs = [];
        let cells = [];
        let rowcount = (style.gridTemplateRows.match(/ /g)||[]).length + 1;
        let colcount = (style.gridTemplateColumns.match(/ /g)||[]).length + 1;
        while (program_master.hasChildNodes()) program_master.removeChild(program_master.firstChild);

        for (let y = 0; y < rowcount; ++y)
        {
            let subcells = [];
            for (let x = 0; x < colcount; ++x) subcells.push(false);
            cells.push(subcells);
        }

        for (let program_index in program_info) programs.push(program_info[program_index]);
        programs.sort((a, b) => b['width'] * b['height'] - a['width'] * a['height']);

        for (let program of programs)
        {
            let program_name = program['display-name'];
            let program_url = program['url'];
            let icon_image = program['icon-image'];
            let width = program['width'];
            let height = program['height'];
            let type = program['program-type'];
            if (type < 0 || type >= program_colors.length) continue;

            let startx = Math.round(Math.random() * colcount);
            let starty = Math.round(Math.random() * rowcount);
            let cellx = null;
            let celly = null;

            for (let i = 0; i < rowcount; ++i)
            {
                for (let j = 0; j < colcount; ++j)
                {
                    let y = (starty + i) % rowcount;
                    let x = (startx + j) % colcount;
                    if (y + height >= rowcount || x + width >= colcount) continue;
                    let isopen = true;

                    for (let a = 0; a < height; ++a)
                    {
                        for (let b = 0; b < width; ++b)
                        {
                            if (cells[a + y][b + x])
                            {
                                isopen = false;
                                break;
                            }
                        }

                        if (!isopen) break;
                    }

                    if (isopen)
                    {
                        cellx = x;
                        celly = y;

                        for (let a = 0; a < height; ++a)
                        {
                            for (let b = 0; b < width; ++b)
                            {
                                cells[a + y][b + x] = true;
                            }
                        }

                        break;
                    }
                }

                if (cellx !== null && celly !== null) break;
            }

            if (cellx === null || celly === null) continue;
            let program_cont = document.createElement('div');
            let program_image = document.createElement('img');
            let program_header = document.createElement('h6');
            program_cont.className = 'program';
            program_header.innerText = program_name;
            if (program_url.startsWith('/')) program_url = location.href + program_url.substring(1);
            if (program_name === null && program_url === null) program_cont.title = 'N/A';
            else if (program_name === null) program_cont.title = program_url;
            else if (program_url === null) program_cont.title = program_name;
            else program_cont.title = `${program_name}\n${program_url}`;
            if (icon_image === null && program_url !== null) program_image.src = `https://s2.googleusercontent.com/s2/favicons?domain_url=${program_url}`;
            else if (icon_image !== null) program_image.src = `/image/icon/${icon_image}`;
            program_cont.style.gridArea = `${celly + 1}/${cellx + 1}/span ${height}/span ${width}`;
            program_cont.style.borderColor = program_colors[type];
            if (program_url !== null) program_cont.addEventListener('click', (e) => window.open(program_url, '_blank'));
            program_cont.appendChild(program_image);
            if (program_name !== null) program_cont.appendChild(program_header);
            program_master.appendChild(program_cont);
        }
    }

    function propagate_contact_info(contact_info)
    {
        let contact_listing = document.getElementById('contact-info-container').firstElementChild;

        for (let contact of Object.values(contact_info))
        {
            let contact_container = document.createElement('a');
            let contact_icon = document.createElement('img');
            let contact_header = document.createElement('h6');
            let contact_url = contact['url'];

            contact_container.className = 'contact';
            contact_icon.src = `/image/icon/${contact['icon-image']}`;
            contact_header.innerText = contact['display-name'];

            if (contact_url !== null)
            {
                contact_container.style.cursor = 'cursor';
                contact_container.href = contact_url;
                contact_container.target = '_blank';
                contact_container.title = `${contact_header.innerText}\n${contact_url}`;
            }
            else contact_container.style.cursor = 'unset';

            contact_container.appendChild(contact_icon);
            contact_container.appendChild(contact_header);
            contact_listing.appendChild(contact_container);
        }
    }

    // Retrieve program info
    {
        window.fetch('/connect-init', {headers: {'Content-Type': 'application/json'}, method: 'POST'}).then(async (response) => {
            let json = JSON.parse(await response.text());
            if (json == null) return;
            propagate_game_info(json['game-storage']);
            propagate_program_info(json['program-storage']);
            propagate_contact_info(json['contact-storage']);
            window.addEventListener('resize', (e) => propagate_program_info(json['program-storage']));
        });
    }

    // Navbar Animation
    {
        window.addEventListener('load', (e) => {
            let navbar = $('nav#navbar');
            let children = navbar.children();
            let bounds = navbar[0].getBoundingClientRect();
            let navbar_height = bounds.bottom;
            let navbar_visible = true;

            window.addEventListener('mousemove', (event) => {
               let mousey = event.pageY - window.scrollY;

               if (mousey <= navbar_height && !navbar_visible)
               {
                   navbar.stop().animate({
                       backgroundColor: '#000000',
                       height: '10vh',
                       borderBottomColor: '#eeeeee',
                   });
                   children.stop().fadeIn();
                   navbar_visible = true;
               }
               else if (mousey > navbar_height && navbar_visible)
               {
                   navbar.stop().animate({
                       backgroundColor: 'rgba(0, 0, 0, 0.125)',
                       height: '2.5vh',
                       borderBottomColor: 'rgba(238, 238, 238, 0.125)',
                   });
                   children.stop().fadeOut();
                   navbar_visible = false;
               }
            });
        });
    }

    // Navbar Actions
    {
        window.addEventListener('load', (e) => {
            let query = new URLSearchParams(window.location.search);
            let prompt = query.get('prompt');
            let admin_login_button = document.getElementById('action-admin-login');
            let admin_login_modal = document.getElementById('admin-login-container');
            let admin_login_close_button = document.getElementById('action-admin-login-close');
            let admin_login_form = document.getElementById('admin-login');
            admin_login_button.addEventListener('click', (e) => window.fetch('/admin', {method: 'GET'}).then((response) => {
                if (response.ok) window.open('/admin', '_self');
                else window.open(response.url, '_self');
            }));
            admin_login_close_button.addEventListener('click', (e) => {
                admin_login_modal.close();
                admin_login_form.reset();
            });
            if (query.get('adminlogin') === '1') admin_login_modal.showModal();
            if (prompt !== null) alert(prompt);

            document.querySelectorAll('a[href^="#"]').forEach(anchor => {
                anchor.addEventListener('click', function (e) {
                    e.preventDefault();
                    document.querySelector(this.getAttribute('href')).scrollIntoView({behavior: 'smooth'});
                });
            });

            window.fetch('/admin/current-user', {method: 'POST', headers: {'Content-Type': 'application/json'}}).then(async (response) => {
                let img = document.getElementById('user-icon');

                if (!response.ok)
                {
                    img.src = '';
                    img.title = 'N/A';
                    img.onclick = null;
                    img.style.cursor = 'unset';
                    return;
                }

                let json = await response.json();
                let b64 = json['usericon'];
                if (b64 === null || b64 === undefined) return;
                img.src = `data:image/jpeg;base64,${b64}`;
                img.title = json['username'];
                img.onclick = (e) => window.open('/admin', '_self');
                img.style.cursor = 'pointer';
            });
        });
    }
}