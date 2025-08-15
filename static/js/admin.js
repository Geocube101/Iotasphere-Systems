{
    let session_user_info = null;

    function arrayBufferToBase64(buffer)
    {
        let binary = '';
        let bytes = new Uint8Array( buffer );
        let len = bytes.byteLength;
        for (let i = 0; i < len; i++) binary += String.fromCharCode( bytes[ i ] );
        return window.btoa( binary );
    }

    function show_image(image)
    {
        if (image === undefined || image === null || image.src === undefined || image.src === null) return;
        let win = window.open('', '_blank');
        let img = document.createElement('img');
        img.src = image.src;
        img.style.flexGrow = '0';
        img.style.flexShrink = '0';
        win.document.body.appendChild(img);
        win.document.body.style.backgroundColor = '#111111';
        win.document.body.style.display = 'flex';
        win.document.body.style.alignItems = 'center';
        win.document.body.style.justifyContent = 'center';
    }

    function update_session_user_info()
    {
        window.fetch('/admin/current-user', {method: 'POST', headers: {'Content-Type': 'application/json'}}).then(async (response) => {
            let usericon = document.getElementById('current-user-profile-img');
            let username = document.getElementById('current-user-name');
            let useraccess = document.getElementById('current-user-access');
            let access = ['Super-User', 'Administrator', 'Moderator'];

            if (response.ok)
            {
                session_user_info = await response.json();
                let base64 = session_user_info['usericon'];
                usericon.src = (base64 === null || base64 === undefined) ? '' : `data:image/jpeg;base64,${base64}`;
                username.innerText = session_user_info['username'];
                useraccess.innerText = access[session_user_info['access-type']];
            }
            else
            {
                session_user_info = null;
                usericon.src = '';
                username.innerText = 'N/A';
                useraccess.innerText = 'N/A';
            }
        });
    }

    // Session Management
    {
        window.addEventListener('load', (e) => {
            let socket = io(`${window.location.host}/admin`);
            let token = null;
            let interval = undefined;

            socket.on('disconnect', (e) => {
                window.clearInterval(interval);
                alert('Panel Disconnected');
                location.replace('/');
            });

            socket.on('begin-session-response', (value, tok) => {
                if (!value) location.replace('/');
                token = tok;
                setup_navbar_actions();
                update_session_user_info();
                interval = window.setInterval(() => socket.emit('session-tick', token), 300000);
            })

            socket.emit('request-begin-session');
        });
    }

    // Contacts Section
    {
        let contacts_container = document.getElementById('contacts-container');
        let listing = contacts_container.querySelector('#contacts-list');

        async function submit_contact_listing(e)
        {
            e.preventDefault();
            let hidden_icon = document.getElementById('contact-editor-contact-icon-image-data');
            let icon_input = document.getElementById('contact-editor-contact-icon-image');
            let icon_file = icon_input.files[0];

            if (icon_file !== undefined)
            {
                let raw = await icon_file.arrayBuffer();
                hidden_icon.value = arrayBufferToBase64(raw);
            }

            window.fetch('/admin/contact-editor', {method: 'POST', body: new FormData(document.getElementById('contact-editor'))})
                .then(async (response) => {
                    if (!response.ok)
                    {
                        alert(`Failed to update contact listing:\n${await response.text()}`);
                        return;
                    }

                    document.getElementById('contact-editor-container').close();
                    update_contacts_listing();
                });
        }

        function open_contact_editor(contact_name, contact)
        {
            let dialog = document.getElementById('contact-editor-container');
            let icon_image = contact['icon-image'];
            let icon_img = document.getElementById('contact-editor-contact-icon-img');
            let contact_type = document.getElementById('contact-editor-contact-type');
            let contact_full_url = document.getElementById('contact-editor-contact-url');
            let contact_content = document.getElementById('contact-editor-contact-content');
            document.getElementById('contact-editor-contact-id').value = contact_name;
            document.getElementById('contact-editor-contact-name').value = contact['display-name'];
            document.getElementById('contact-editor-contact-visible').checked = contact['visible'];
            contact_content.value = contact['content'];
            contact_type.value = `${contact['contact-type']}`;
            contact_full_url.value = contact['url'];
            document.getElementById('contact-editor-delete').onclick = (e) => {
                if (!window.confirm('Delete Contact?')) return;
                window.fetch('/admin/contacts-del', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({'contact-id': contact_name})}).then(async (response) => {
                    if (response.ok) update_contacts_listing((await response.json()));
                    else alert(`Failed to delete contact:\n${await response.text()}`);
                    dialog.close();
                });
            };
            contact_type.onchange = (e) => {
                switch (contact_type.value)
                {
                    case '1':
                        contact_full_url.value = contact_content.value;
                        break;
                    case '2':
                        contact_full_url.value = `mailto:${contact_content.value}`;
                        break;
                    case '3':
                        contact_full_url.value = `tel:${contact_content.value}`;
                        break;
                    default:
                        contact_full_url.value = '';
                        break;
                }
            };
            if (icon_image !== null) icon_img.src = `/image/icon/${icon_image}`;
            else icon_img.src = '';
            icon_img.onclick = (e) => show_image(icon_img);
            dialog.showModal();
        }

        function update_contacts_listing(contacts_listing = undefined)
        {
            function internal_update(contacts_list)
            {
                while (listing.hasChildNodes()) listing.removeChild(listing.firstChild);

                for (let [contactid, contact] of Object.entries(contacts_list))
                {
                    console.log(contact);
                    let enabled = contact['visible'];
                    let icon_image = contact['icon-image'];
                    let contact_container = document.createElement('div');
                    let image_icon = document.createElement('img');
                    let contact_name_p = document.createElement('p');
                    let edit_action = document.createElement('button');
                    let remove_action = document.createElement('button');

                    contact_container.className = 'contact-listing';
                    image_icon.src = `/image/icon/${icon_image}`;
                    contact_name_p.innerText = contact['display-name'];
                    contact_name_p.style.fontStyle = (enabled) ? 'normal' : 'italic';
                    contact_name_p.style.color = (enabled) ? '#eeeeee' : '#888888';
                    edit_action.innerText = 'Edit';
                    edit_action.addEventListener('click', (e) => open_contact_editor(contactid, contact));
                    remove_action.innerText = 'Delete';
                    remove_action.className = 'delete-button';
                    remove_action.addEventListener('click', (e) => {
                        if (!window.confirm('Delete Contact?')) return;
                        window.fetch('/admin/contacts-del', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({'contact-id': contactid})}).then(async (response) => {
                            if (response.ok) update_contacts_listing((await response.json()));
                            else alert(`Failed to delete contact:\n${await response.text()}`);
                        });
                    });

                    contact_container.appendChild(image_icon);
                    contact_container.appendChild(contact_name_p);
                    contact_container.appendChild(edit_action);
                    contact_container.appendChild(remove_action);
                    listing.appendChild(contact_container);
                }
            }

            if (contacts_listing === undefined)
            {
                window.fetch('/admin/contacts-list', {method: 'POST', headers: {'Content-Type': 'application/json'}}).then(async (response) => {
                    if (response.ok) internal_update((await response.json()));
                    else alert(`Failed to download contacts listing:\n${await response.text()}`);
                });
            }
            else
            {
                internal_update(contacts_listing);
            }
        }

        document.getElementById('contact-editor').addEventListener('submit', submit_contact_listing);
        document.getElementById('contact-editor-close').addEventListener('click', (e) => document.getElementById('contact-editor-container').close());
        document.getElementById('add-contact-button').addEventListener('click', (e) => {
            window.fetch('/admin/contacts-add', {method: 'POST', headers: {'Content-Type': 'application/json'}}).then(async (response) => {
                if (!response.ok)
                {
                    alert(`Failed to add contact:\n${await response.text()}`);
                    return;
                }

                let json = await response.json();
                let new_contact_id = json['new'];
                let contacts = json['body'];
                update_contacts_listing(contacts);
                open_contact_editor(new_contact_id, contacts[new_contact_id]);
            });
        });

        contacts_container.ondisplaychange = (element, is_visible) => {
            if (is_visible) update_contacts_listing();
        };
    }

    // Programs Section
    {
        let programs_container = document.getElementById('programs-container');
        let tbody = programs_container.getElementsByTagName('tbody')[0];

        async function submit_program_listing(e)
        {
            e.preventDefault();
            let hidden_icon = document.getElementById('program-editor-program-icon-image-data');
            let icon_input = document.getElementById('program-editor-program-icon-image');
            let icon_file = icon_input.files[0];

            if (icon_file !== undefined)
            {
                let raw = await icon_file.arrayBuffer();
                hidden_icon.value = arrayBufferToBase64(raw);
            }

            window.fetch('/admin/program-editor', {method: 'POST', body: new FormData(document.getElementById('program-editor'))})
                .then(async (response) => {
                    if (!response.ok)
                    {
                        alert(`Failed to update program listing:\n${await response.text()}`);
                        return;
                    }

                    document.getElementById('program-editor-container').close();
                    update_programs_listing();
                });
        }

        function open_program_editor(program_name, program)
        {
            let dialog = document.getElementById('program-editor-container');
            let icon_image = program['icon-image'];
            let icon_img = document.getElementById('program-editor-program-icon-img');
            document.getElementById('program-editor-program-id').value = program_name;
            document.getElementById('program-editor-program-name').value = program['display-name'];
            document.getElementById('program-editor-program-url').value = program['url'];
            document.getElementById('program-editor-program-visible').checked = program['visible'];
            document.getElementById('program-editor-program-width').value = `${program['width']}`;
            document.getElementById('program-editor-program-height').value = `${program['height']}`;
            document.getElementById('program-editor-program-type').value = `${program['program-type']}`;
            document.getElementById('program-editor-delete').onclick = (e) => {
                if (!window.confirm('Delete Program?')) return;
                window.fetch('/admin/programs-del', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({'program-id': program_name})}).then(async (response) => {
                    if (response.ok) update_programs_listing((await response.json()));
                    else alert(`Failed to delete program:\n${await response.text()}`);
                    dialog.close();
                });
            };
            if (icon_image !== null) icon_img.src = `/image/icon/${icon_image}`;
            else icon_img.src = '';
            icon_img.onclick = (e) => show_image(icon_img);
            dialog.showModal();
        }

        function update_programs_listing(programs_listing = undefined)
        {
            function internal_update(programs_list)
            {
                while (tbody.hasChildNodes()) tbody.removeChild(tbody.firstChild);
                let max_col_count = 10;
                let count = 0;
                let row = document.createElement('tr');
                let program_colors = ['#EEEEEE', '#EB4034', '#C634EB', '#34EB62', '#EB9334'];
                let programs = [];
                for (let [program_name, program] of Object.entries(programs_list)) programs.push([program_name, program]);

                for (let i = 0; i < Math.max(40, programs.length); ++i)
                {
                    let cell = document.createElement('td');
                    let program_cont = document.createElement('img');
                    let data = programs[i];

                    if (data !== undefined)
                    {
                        let prgm_name = data[0];
                        let program = data[1];
                        let icon_image = program['icon-image'];
                        let program_url = program['url'];
                        let type = program['program-type'];
                        let program_name = program['display-name'];
                        program_cont.style.cursor = 'pointer';
                        if (program_name === null && program_url === null) program_cont.title = 'N/A';
                        else if (program_name === null) program_cont.title = program_url;
                        else if (program_url === null) program_cont.title = program_name;
                        else program_cont.title = `${program_name}\n${program_url}`;
                        if (icon_image === null && program_url !== null) program_cont.src = `https://s2.googleusercontent.com/s2/favicons?domain_url=${program_url}`;
                        else if (icon_image !== null) program_cont.src = `/image/icon/${icon_image}`;
                        program_cont.style.borderColor = program_colors[type];
                        program_cont.addEventListener('click', (e) => open_program_editor(prgm_name, program));
                    }
                    else program_cont.style.border = 'none';

                    cell.appendChild(program_cont);
                    row.appendChild(cell);
                    if (++count % max_col_count !== 0) continue;
                    tbody.appendChild(row);
                    row = document.createElement('tr');
                }
            }

            if (programs_listing === undefined)
            {
                window.fetch('/admin/programs-list', {method: 'POST', headers: {'Content-Type': 'application/json'}}).then(async (response) => {
                    if (response.ok) internal_update((await response.json()));
                    else alert(`Failed to download programs listing:\n${await response.text()}`);
                });
            }
            else
            {
                internal_update(programs_listing);
            }
        }

        document.getElementById('program-editor').addEventListener('submit', submit_program_listing);
        document.getElementById('program-editor-close').addEventListener('click', (e) => document.getElementById('program-editor-container').close());
        document.getElementById('add-program-button').addEventListener('click', (e) => {
            window.fetch('/admin/programs-add', {method: 'POST', headers: {'Content-Type': 'application/json'}}).then(async (response) => {
                if (!response.ok)
                {
                    alert(`Failed to add program:\n${await response.text()}`);
                    return;
                }

                let json = await response.json();
                let new_program_id = json['new'];
                let programs = json['body'];
                update_programs_listing(programs);
                open_program_editor(new_program_id, programs[new_program_id]);
            });
        });

        programs_container.ondisplaychange = (element, is_visible) => {
            if (is_visible) update_programs_listing();
        };
    }

    // Games Section
    {
        async function submit_game_listing(e)
        {
            e.preventDefault();
            let hidden_icon = document.getElementById('game-editor-game-icon-image-data');
            let hidden_background = document.getElementById('game-editor-game-bg-image-data');
            let icon_input = document.getElementById('game-editor-game-icon-image');
            let background_input = document.getElementById('game-editor-game-bg-image');
            let section_form_data = document.getElementById('game-editor-game-sections');
            let icon_file = icon_input.files[0];
            let background_file = background_input.files[0];

            if (icon_file !== undefined)
            {
                let raw = await icon_file.arrayBuffer();
                hidden_icon.value = arrayBufferToBase64(raw);
            }

            if (background_file !== undefined)
            {
                let raw = await background_file.arrayBuffer();
                hidden_background.value = arrayBufferToBase64(raw);
            }

            let modified_section_info = {};

            for (let [section_name, section] of Object.entries(game_section_data))
            {
                if (modified_sections.indexOf(section_name) === -1) continue;
                else if (section === null)
                {
                    modified_section_info[section_name] = null;
                    continue;
                }

                let modified_children_info = {};
                for (let [child_index, child] of Object.entries(section['children'])) if (is_child_modified(section_name, child_index)) modified_children_info[child_index] = child;

                modified_section_info[section_name] = JSON.parse(JSON.stringify(section), (key, val, context) => {
                    if (key === 'children') return modified_children_info;
                    else return val;
                });
            }

            section_form_data.value = JSON.stringify(modified_section_info);
            game_section_data = undefined;
            modified_sections.length = 0;
            modified_children.length = 0;

            window.fetch('/admin/game-editor', {method: 'POST', body: new FormData(document.getElementById('game-editor'))})
                .then(async (response) => {
                    if (!response.ok)
                    {
                        alert(`Failed to update game listing:\n${await response.text()}`);
                        return;
                    }

                    document.getElementById('game-editor-container').close();
                    update_games_listing();
                });
        }

        function open_child_editor(game_name, game, section_name, section_data, child_name)
        {
            let parent = document.getElementById('game-section-editor-container');
            let dialog = document.getElementById('game-child-editor-container');
            let form = document.getElementById('game-child-editor');
            let child_name_inp = document.getElementById('game-child-editor-child-name');
            let child_url_inp = document.getElementById('game-child-editor-child-url');
            let child_visible_inp = document.getElementById('game-child-editor-child-visible');
            let child_data = section_data['children'][child_name];
            let icon_image = child_data['icon-image'];

            parent.close();
            child_name_inp.value = child_data['display-name'];
            child_url_inp.value = child_data['url'];
            child_visible_inp.checked = child_data['visible'];
            if (icon_image !== null) document.getElementById('game-child-editor-child-icon-img').src = `/image/icon/${icon_image}`;
            else document.getElementById('game-child-editor-child-icon-img').src = '';

            form.onsubmit = async (e) => {
                e.preventDefault();

                let icon_input = document.getElementById('game-child-editor-child-icon-image');
                let icon_file = icon_input.files[0];
                let icon_image = '';

                if (icon_file !== undefined)
                {
                    let raw = await icon_file.arrayBuffer();
                    icon_image = arrayBufferToBase64(raw);
                }

                child_data['display-name'] = child_name_inp.value;
                child_data['url'] = child_url_inp.value;
                child_data['visible'] = child_visible_inp.checked;
                child_data['new-icon-image'] = icon_image;

                modified_children.push([section_name, child_name]);
                update_children_listing(game_name, game, section_name);

                parent.showModal();
                dialog.close();
            };

            dialog.showModal();
        }

        function open_section_editor(game_name, game, section_name, section_data)
        {
            let parent = document.getElementById('game-editor-container');
            let dialog = document.getElementById('game-section-editor-container');
            let form = document.getElementById('game-section-editor');
            let section_name_inp = document.getElementById('game-section-editor-section-name');
            let section_visible_inp = document.getElementById('game-section-editor-section-visible');
            let bg_image = section_data['background-image'];

            parent.close();
            section_name_inp.value = section_data['display-name'];
            section_visible_inp.checked = section_data['visible'];
            if (bg_image !== null) document.getElementById('game-section-editor-section-background-image').src = `/image/background/${bg_image}`;
            else document.getElementById('game-section-editor-section-background-image').src = '';
            update_children_listing(game_name, game, section_name);
            document.getElementById('add-child-button').onclick = (e) => {
                let child_name = crypto.randomUUID();
                while (uuids.indexOf(child_name) !== -1) child_name = crypto.randomUUID();
                section_data['children'][child_name] = {
                    'visible': false,
                    'display-name': '',
                    'url': null,
                    'icon-image': null,
                };
                uuids.push(section_name);
                modified_sections.push(section_name);
                modified_children.push([section_name, child_name]);
                open_child_editor(game_name, game, section_name, section_data, child_name);
            };

            form.onsubmit = async (e) => {
                e.preventDefault();

                let background_input = document.getElementById('game-section-editor-section-background-image');
                let background_file = background_input.files[0];
                let background_image = '';

                if (background_file !== undefined)
                {
                    let raw = await background_file.arrayBuffer();
                    background_image = arrayBufferToBase64(raw);
                }

                section_data['display-name'] = section_name_inp.value;
                section_data['visible'] = section_visible_inp.checked;
                section_data['new-background-image'] = background_image;

                modified_sections.push(section_name);
                update_sections_listing(game_name, game);

                parent.showModal();
                dialog.close();
            };

            dialog.showModal();
        }

        function open_game_editor(game_name, game)
        {
            let dialog = document.getElementById('game-editor-container');
            let icon_image = game['icon-image'];
            let background_image = game['background-image'];
            let icon_img = document.getElementById('game-editor-game-icon-img');
            let bg_img = document.getElementById('game-editor-game-bg-img');

            game_section_data = game['sections'];
            document.getElementById('game-editor-game-id').value = `${game_name}`;
            document.getElementById('game-editor-game-name').value = game['display-name'];
            document.getElementById('game-editor-game-url').value = game['game-url'];
            document.getElementById('game-editor-game-visible').checked = game['visible'];
            document.getElementById('add-section-button').onclick = (e) => {
                let section_name = crypto.randomUUID();
                while (uuids.indexOf(section_name) !== -1) section_name = crypto.randomUUID();
                let section_data = {
                    'visible': false,
                    'display-name': '',
                    'background-image': null,
                    'children': {}
                };
                uuids.push(section_name);
                game_section_data[section_name] = section_data;
                modified_sections.push(section_name);
                open_section_editor(game_name, game, section_name, section_data);
            };
            if (icon_image !== null) icon_img.src = `/image/icon/${icon_image}`;
            else icon_img.src = '';
            if (background_image !== null) bg_img.src = `/image/background/${background_image}`;
            else bg_img.src = '';
            icon_img.onclick = (e) => show_image(icon_img);
            bg_img.onclick = (e) => show_image(bg_img);
            update_sections_listing(game_name, game);
            dialog.showModal();
        }

        function update_children_listing(game_name, game, section_name)
        {
            if (game_section_data === undefined) return;
            let children_container = document.getElementById('game-section-editor-child-container');
            while (children_container.hasChildNodes()) children_container.removeChild(children_container.firstChild);

            for (let [child_name, child] of Object.entries(game_section_data[section_name]['children']))
            {
                let child_container = document.createElement('div');
                let child_image = document.createElement('img');
                let child_title = document.createElement('p');
                let edit_child = document.createElement('button');
                let remove_child = document.createElement('button');
                let child_visible = child['visible'];
                let icon_image = child['icon-image'];

                edit_child.innerText = 'Edit';
                edit_child.type = 'button';
                remove_child.innerText = 'Delete';
                remove_child.type = 'button';
                remove_child.className = 'delete-button';
                child_title.innerText = child['display-name'];
                child_title.style.fontStyle = (child_visible) ? 'normal' : 'italic';
                child_title.style.color = (child_visible) ? '#eeeeee' : '#888888';
                if (icon_image !== null) child_image.src = `/image/icon/${icon_image}`;

                if (is_child_modified(section_name, child_name))
                {
                    child_title.style.fontStyle = 'italic';
                    child_title.style.color = '#AA0000';
                }

                edit_child.addEventListener('click', (e) => {
                    open_child_editor(game_name, game, section_name, game_section_data[section_name], child_name);
                });

                remove_child.addEventListener('click', (e) => {
                    if (!window.confirm('Delete Section?')) return;
                    game_section_data[section_name]['children'][child_name] = null;
                    children_container.removeChild(child_container);
                    modified_children.push([section_name, child_name]);
                });

                child_container.appendChild(child_image);
                child_container.appendChild(child_title);
                child_container.appendChild(edit_child);
                child_container.appendChild(remove_child);
                children_container.appendChild(child_container);
            }
        }

        function update_sections_listing(game_name, game)
        {
            let sections_container = document.getElementById('game-editor-section-container');
            while (sections_container.hasChildNodes()) sections_container.removeChild(sections_container.firstChild);

            for (let [section_name, section] of Object.entries(game_section_data))
            {
                let section_container = document.createElement('div');
                let section_image = document.createElement('img');
                let section_title = document.createElement('p');
                let edit_section = document.createElement('button');
                let remove_section = document.createElement('button');
                let section_visible = section['visible'];

                edit_section.innerText = 'Edit';
                edit_section.type = 'button';
                remove_section.innerText = 'Delete';
                remove_section.type = 'button';
                remove_section.className = 'delete-button';
                section_title.innerText = section['display-name'];
                section_title.style.fontStyle = (section_visible) ? 'normal' : 'italic';
                section_title.style.color = (section_visible) ? '#eeeeee' : '#888888';

                if (modified_sections.indexOf(section_name) !== -1)
                {
                    section_title.style.fontStyle = 'italic';
                    section_title.style.color = '#AA0000';
                }

                edit_section.addEventListener('click', (e) => {
                    open_section_editor(game_name, game, section_name, game_section_data[section_name]);
                });

                remove_section.addEventListener('click', (e) => {
                    if (!window.confirm('Delete Section?')) return;
                    game_section_data[section_name] = null;
                    sections_container.removeChild(section_container);
                    modified_sections.push(section_name);
                });

                section_container.appendChild(section_image);
                section_container.appendChild(section_title);
                section_container.appendChild(edit_section);
                section_container.appendChild(remove_section);
                sections_container.appendChild(section_container);
            }
        }

        function update_games_listing(games_listing = undefined)
        {
            function internal_update(games_list)
            {
                while (listing.hasChildNodes()) listing.removeChild(listing.firstChild);

                for (let [game_name, game] of Object.entries(games_list))
                {
                    let icon_image = game['icon-image'];
                    let visible = game['visible'];
                    let game_container = document.createElement('div');
                    let image_icon = document.createElement('img');
                    let game_name_p = document.createElement('p');
                    let edit_action = document.createElement('button');
                    let remove_action = document.createElement('button');

                    game_container.className = 'game-listing';
                    if (icon_image !== null) image_icon.src = `/image/icon/${icon_image}`;
                    game_name_p.innerText = game['display-name'];
                    game_name_p.style.fontStyle = (visible) ? 'normal' : 'italic';
                    game_name_p.style.color = (visible) ? '#eeeeee' : '#888888';
                    edit_action.innerText = 'Edit';
                    edit_action.addEventListener('click', (e) => open_game_editor(game_name, game));
                    remove_action.innerText = 'Delete';
                    remove_action.className = 'delete-button';
                    remove_action.addEventListener('click', (e) => {
                        if (!window.confirm('Delete Game?')) return;
                        window.fetch('/admin/games-del', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({'game-id': game_name})}).then(async (response) => {
                            if (response.ok) update_games_listing((await response.json()));
                            else alert(`Failed to delete game:\n${await response.text()}`);
                        });
                    });

                    game_container.appendChild(image_icon);
                    game_container.appendChild(game_name_p);
                    game_container.appendChild(edit_action);
                    game_container.appendChild(remove_action);
                    listing.appendChild(game_container);
                }
            }

            if (games_listing === undefined)
            {
                window.fetch('/admin/games-list', {method: 'POST', headers: {'Content-Type': 'application/json'}}).then(async (response) => {
                    if (response.ok) internal_update((await response.json()));
                    else alert(`Failed to download games listing:\n${await response.text()}`);
                });
            }
            else
            {
                internal_update(games_listing);
            }
        }

        function is_child_modified(section_name, child_index)
        {
            for (let [sn, ci] of modified_children) if (sn === section_name && ci === child_index) return true;
            return false;
        }

        let games_container = document.getElementById('games-container');
        let listing = games_container.querySelector('#games-list');
        let game_section_data = undefined;
        let modified_sections = [];
        let modified_children = [];
        let uuids = [];

        document.getElementById('game-editor').addEventListener('submit', submit_game_listing);
        document.getElementById('game-editor-close').addEventListener('click', (e) => {
            game_section_data = undefined;
            modified_sections.length = 0;
            modified_children.length = 0;
            document.getElementById('game-editor-container').close();
        });
        document.getElementById('game-section-editor-close').addEventListener('click', (e) => {
            document.getElementById('game-section-editor-container').close();
            document.getElementById('game-editor-container').showModal();
        });
        document.getElementById('game-child-editor-close').addEventListener('click', (e) => {
            document.getElementById('game-child-editor-container').close();
            document.getElementById('game-section-editor-container').showModal();
        });
        document.getElementById('add-game-button').addEventListener('click', (e) => {
            window.fetch('/admin/games-add', {method: 'POST', headers: {'Content-Type': 'application/json'}}).then(async (response) => {
                if (!response.ok)
                {
                    alert(`Failed to add game:\n${await response.text()}`);
                    return;
                }

                let json = await response.json();
                let new_game_id = json['new'];
                let games = json['body'];
                update_games_listing(games);
                open_game_editor(new_game_id, games[new_game_id]);
            });
        });

        games_container.ondisplaychange = (element, is_visible) => {
            if (is_visible) update_games_listing();
        };
    }

    // Users Section
    {
        let users_container = document.getElementById('users-container');
        let listing = users_container.querySelector('#users-list');

        async function submit_user_listing(e)
        {
            e.preventDefault();
            let hidden_icon = document.getElementById('user-editor-user-icon-image-data');
            let icon_input = document.getElementById('user-editor-user-icon-image');
            document.getElementById('user-editor-user-expire-ts').value = `${document.getElementById('user-editor-user-expire').valueAsNumber}`;
            let icon_file = icon_input.files[0];

            if (icon_file !== undefined)
            {
                let raw = await icon_file.arrayBuffer();
                hidden_icon.value = arrayBufferToBase64(raw);
            }

            window.fetch('/admin/user-editor', {method: 'POST', body: new FormData(document.getElementById('user-editor'))})
                .then(async (response) => {
                    if (!response.ok)
                    {
                        alert(`Failed to update user listing:\n${await response.text()}`);
                        return;
                    }

                    document.getElementById('user-editor-container').close();
                    update_users_listing();
                    update_session_user_info();
                });
        }

        function delete_user(userid, dailog = undefined)
        {
            if (!window.confirm('Delete User?')) return;
            window.fetch('/admin/users-del', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({'user-id': userid})}).then(async (response) => {
                if (response.ok) update_programs_listing((await response.json()));
                else alert(`Failed to delete user:\n${await response.text()}`);
                if (dialog !== undefined) dialog.close();
                update_session_user_info();
            });
        }

        function open_user_editor(userid, user)
        {
            let dialog = document.getElementById('user-editor-container');
            let icon_img = document.getElementById('user-editor-user-icon-img');
            let expires = user['expires'] !== null;
            let expire = document.getElementById('user-editor-user-expire');
            let does_expire = document.getElementById('user-editor-user-expires');
            let password = document.getElementById('user-editor-user-password');
            document.getElementById('user-editor-user-id').value = userid;
            document.getElementById('user-editor-user-name').value = user['username'];
            document.getElementById('user-editor-user-email').value = user['usermail'];
            does_expire.checked = expires;
            does_expire.onchange = (e) => expire.disabled = !does_expire.checked;
            expire.valueAsNumber = user['expires'];
            expire.disabled = !expires;
            password.disabled = session_user_info === null || session_user_info['access-type'] > 0;
            document.getElementById('user-editor-user-enabled').checked = user['enabled'];
            document.getElementById('user-editor-user-type').value = `${user['access-type']}`;
            document.getElementById('user-editor-delete').onclick = (e) => delete_user(userid, dialog);
            let imageb64 = user['usericon'];
            icon_img.src = (imageb64 === null || imageb64 === undefined) ? '' : `data:image/jpeg;base64,${imageb64}`;
            icon_img.onclick = (e) => show_image(icon_img);
            dialog.showModal();
        }

        function update_users_listing(users_listing = undefined)
        {
            function internal_update(users_list)
            {
                while (listing.hasChildNodes()) listing.removeChild(listing.firstChild);

                for (let [userid, user] of Object.entries(users_list))
                {
                    let enabled = user['enabled'];
                    let imageb64 = user['usericon'];
                    let user_container = document.createElement('div');
                    let image_icon = document.createElement('img');
                    let user_name_p = document.createElement('p');
                    let edit_action = document.createElement('button');
                    let remove_action = document.createElement('button');

                    user_container.className = 'user-listing';
                    image_icon.src = (imageb64 === null || imageb64 === undefined) ? '' : `data:image/jpeg;base64,${imageb64}`;
                    user_name_p.innerText = user['username'];
                    user_name_p.style.fontStyle = (enabled) ? 'normal' : 'italic';
                    user_name_p.style.color = (enabled) ? '#eeeeee' : '#888888';
                    edit_action.innerText = 'Edit';
                    edit_action.addEventListener('click', (e) => open_user_editor(userid, user));
                    remove_action.innerText = 'Delete';
                    remove_action.className = 'delete-button';
                    remove_action.addEventListener('click', (e) => delete_user(userid));

                    user_container.appendChild(image_icon);
                    user_container.appendChild(user_name_p);
                    user_container.appendChild(edit_action);
                    user_container.appendChild(remove_action);
                    listing.appendChild(user_container);
                }
            }

            if (users_listing === undefined)
            {
                window.fetch('/admin/users-list', {method: 'POST', headers: {'Content-Type': 'application/json'}}).then(async (response) => {
                    if (response.ok) internal_update((await response.json()));
                    else alert(`Failed to download users listing:\n${await response.text()}`);
                });
            }
            else
            {
                internal_update(users_listing);
            }
        }

        document.getElementById('user-editor').addEventListener('submit', submit_user_listing);
        document.getElementById('user-editor-close').addEventListener('click', (e) => document.getElementById('user-editor-container').close());
        document.getElementById('add-user-button').addEventListener('click', (e) => {
            window.fetch('/admin/user-add', {method: 'POST', headers: {'Content-Type': 'application/json'}}).then(async (response) => {
                if (!response.ok)
                {
                    alert(`Failed to add user:\n${await response.text()}`);
                    return;
                }

                let json = await response.json();
                let new_user_id = json['new'];
                let users = json['body'];
                update_users_listing(users);
                open_user_editor(new_user_id, users[new_user_id]);
            });
        });

        users_container.ondisplaychange = (element, is_visible) => {
            if (is_visible) update_users_listing();
        };
    }

    // Navbar Actions
    function setup_navbar_actions()
    {
        let sections = $('section.main-section');
        let actions = $('nav#navbar button');
        sections.hide();

        let initial_container = $('section.main-section#contacts-container');
        initial_container.show();
        if (initial_container[0].ondisplaychange !== null && initial_container[0].ondisplaychange !== undefined) initial_container[0].ondisplaychange(initial_container[0], true);

        actions.click((e) => {
            let target = e.target.value;
            if (target === '') return window.open('/', '_self');
            sections.hide();
            let visible = $(`section.main-section#${target}`);
            visible.show();

            for (let section of sections)
            {
                if (section.ondisplaychange === null || section.ondisplaychange === undefined) continue;
                section.ondisplaychange(section, section === visible[0]);
            }
        });
    }
}