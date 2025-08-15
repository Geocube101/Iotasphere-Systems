from __future__ import annotations

import json
import PIL.Image

import CustomMethodsVI.FileSystem as FileSystem

import Image
import Util


class MyGameStorageInfo:
    class MyGameSectionInfo:
        def __init__(self, name: str, display_name: str, background_image: int | None, visible: bool):
            self.__visible__: bool = bool(visible)
            self.__section_name__: str = str(name)
            self.__display_name__: str = str(display_name)
            self.__background_image__: int | None = None if background_image is None else int(background_image)
            self.__children__: dict[str, MyGameStorageInfo.MyGameObjectInfo] = {}

        def del_child(self, child_name: str) -> None:
            if child_name in self.__children__:
                del self.__children__[child_name]

        def rename_child(self, old_name: str, new_name: str) -> None:
            if old_name in self.__children__ and old_name != new_name:
                child: MyGameStorageInfo.MyGameObjectInfo = self.__children__[old_name]
                child.__child_name__ = new_name
                self.__children__[new_name] = child
                del self.__children__[old_name]

        def get_child(self, child_name: str) -> MyGameStorageInfo.MyGameObjectInfo | None:
            return self.__children__[child_name] if child_name in self.__children__ else None

        def add_child(self, child_name: str, child_display_name: str, url: str | None, icon_image: int | None, visible: bool) -> MyGameStorageInfo.MyGameObjectInfo:
            assert child_name not in self.__children__
            child: MyGameStorageInfo.MyGameObjectInfo = MyGameStorageInfo.MyGameObjectInfo(self, child_name, child_display_name, url, icon_image, visible)
            self.__children__[child_name] = child
            return child

        def save(self) -> dict:
            return {
                'visible': self.__visible__,
                'display-name': self.__display_name__,
                'background_image': self.__background_image__,
                'children': {c.name: c.save() for c in self.__children__.values()}
            }

        def send_dict(self, visible_only: bool = True) -> dict:
            return {
                'visible': self.__visible__,
                'display-name': self.__display_name__,
                'background_image': None if self.__background_image__ is None else str(self.__background_image__),
                'children': {c.name: c.send_dict() for c in self.__children__.values() if not visible_only or c.visible}
            }

        @property
        def visible(self) -> bool:
            return self.__visible__

        @visible.setter
        def visible(self, visible: bool) -> None:
                self.__visible__ = bool(visible)

        @property
        def section_name(self) -> str:
            return self.__section_name__

        @section_name.setter
        def section_name(self, name: str) -> None:
            assert isinstance(name, str), 'Type error'
            assert 4 <= len(name) <= 64, 'Name length error'
            self.__section_name__ = str(name)

        @property
        def display_name(self) -> str:
            return self.__display_name__

        @display_name.setter
        def display_name(self, name: str) -> None:
            assert isinstance(name, str), 'Type error'
            assert 4 <= len(name) <= 64, 'Name length error'
            self.__display_name__ = str(name)

        @property
        def background_image(self) -> PIL.Image.Image | None:
            if self.__background_image__ is None:
                return None

            return MyGlobalServerStorage.STORAGE.MyImageLoader.MyBackgroundStorage.get_image(self.__background_image__)

        @background_image.setter
        def background_image(self, image: PIL.Image.Image | int | None):
            if self.__background_image__ is not None and image is None:
                MyGlobalServerStorage.STORAGE.MyImageLoader.MyBackgroundStorage.del_image(self.__background_image__)
                self.__background_image__ = None
            elif image is not None:
                self.__background_image__ = int(image) if isinstance(image, int) else MyGlobalServerStorage.STORAGE.MyImageLoader.MyBackgroundStorage.set_image(self.__background_image__, image)

    class MyGameObjectInfo:
        def __init__(self, parent: MyGameStorageInfo.MyGameSectionInfo, name: str, display_name: str, url: str | None, image: int | None, visible: bool):
            assert isinstance(parent, MyGameStorageInfo.MyGameSectionInfo)
            self.__parent__: MyGameStorageInfo.MyGameSectionInfo = parent
            self.__visible__: bool = bool(visible)
            self.__child_name__: str = str(name)
            self.__child_display_name__: str = str(display_name)
            self.__url__: str | None = None if url is None else str(url)
            self.__image__: int | None = None if image is None else int(image)

        def save(self) -> dict:
            return {
                'visible': self.__visible__,
                'display-name': self.__child_display_name__,
                'url': self.__url__,
                'icon-image': None if self.__image__ is None else self.__image__
            }

        def send_dict(self) -> dict:
            return {
                'visible': self.__visible__,
                'display-name': self.__child_display_name__,
                'url': self.__url__,
                'icon-image': None if self.__image__ is None else str(self.__image__)
            }

        @property
        def visible(self) -> bool:
            return self.__visible__

        @visible.setter
        def visible(self, visible: bool) -> None:
            self.__visible__ = bool(visible)

        @property
        def name(self) -> str:
            return self.__child_name__

        @property
        def display_name(self) -> str:
            return self.__child_display_name__

        @display_name.setter
        def display_name(self, name: str) -> None:
            assert isinstance(name, str), 'Type error'
            assert 4 <= len(name) <= 64, 'Name length error'
            self.__child_display_name__ = str(name)
            self.__parent__.rename_child(self.__child_name__, Util.to_functional_name(self.__child_display_name__))

        @property
        def url(self) -> str:
            return self.__url__

        @url.setter
        def url(self, url: str) -> None:
            assert isinstance(url, str), 'Type error'
            self.__url__ = None if url is None or len(str(url)) == 0 else str(url)

        @property
        def icon_image(self) -> PIL.Image.Image | None:
            if self.__image__ is None:
                return None

            return MyGlobalServerStorage.STORAGE.MyImageLoader.MyIconStorage.get_image(self.__image__)

        @icon_image.setter
        def icon_image(self, image: PIL.Image.Image | int | None):
            if self.__image__ is not None and image is None:
                MyGlobalServerStorage.STORAGE.MyImageLoader.MyIconStorage.del_image(self.__image__)
                self.__image__ = None
            elif image is not None:
                self.__image__ = int(image) if isinstance(image, int) else MyGlobalServerStorage.STORAGE.MyImageLoader.MyIconStorage.set_image(self.__image__, image)

    def __init__(self, name: str, display_name: str, url: str, icon_image: int | None, background_image: int | None, visible: bool):
        self.__visible__: bool = bool(visible)
        self.__game_name__: str = str(name)
        self.__game_display_name__: str = str(display_name)
        self.__game_url__: str = str(url)
        self.__icon_image__: int | None = None if icon_image is None else int(icon_image)
        self.__background_image__: int | None = None if background_image is None else int(background_image)
        self.__children__: dict[str, MyGameStorageInfo.MyGameSectionInfo] = {}

    def add_child(self, section_name: str, item_name: str, item_display_name: str, item_url: str, item_image: int | None, visible: bool) -> None:
        assert section_name in self.__children__, f'No such section \'{section_name}\''
        section: MyGameStorageInfo.MyGameSectionInfo = self.__children__[section_name]
        section.add_child(item_name, item_display_name, item_url, item_image, visible)

    def del_section(self, section_name: str) -> None:
        if section_name in self.__children__:
            del self.__children__[section_name]

    def rename_section(self, old_name: str, new_name: str) -> None:
        if old_name in self.__children__ and old_name != new_name:
            section: MyGameStorageInfo.MyGameSectionInfo = self.__children__[old_name]
            section.__child_name__ = new_name
            self.__children__[new_name] = section
            del self.__children__[old_name]

    def add_section(self, section_name: str, section_display_name: str, background_image: int | None, visible: bool) -> MyGameStorageInfo.MyGameSectionInfo:
        section_name = str(section_name)
        assert section_name not in self.__children__, f'Duplicate section \'{section_name}\''
        section: MyGameStorageInfo.MyGameSectionInfo = MyGameStorageInfo.MyGameSectionInfo(section_name, str(section_display_name), background_image, visible)
        self.__children__[section_name] = section
        return section

    def get_section(self, section_name: str) -> MyGameStorageInfo.MyGameSectionInfo | None:
        return self.__children__[section_name] if section_name in self.__children__ else None

    def save(self) -> dict:
        return {
            'visible': self.__visible__,
            'display-name': self.__game_display_name__,
            'game-url': self.__game_url__,
            'icon-image': None if self.__icon_image__ is None else self.__icon_image__,
            'background-image': None if self.__background_image__ is None else self.__background_image__,
            'sections': {k: v.save() for k, v in self.__children__.items()}
        }

    def send_dict(self, visible_only: bool = True) -> dict:
        return {
            'visible': self.__visible__,
            'display-name': self.__game_display_name__,
            'game-url': self.__game_url__,
            'icon-image': None if self.__icon_image__ is None else str(self.__icon_image__),
            'background-image': None if self.__background_image__ is None else str(self.__background_image__),
            'sections': {k: v.send_dict(visible_only) for k, v in self.__children__.items() if not visible_only or v.visible}
        }

    @property
    def visible(self) -> bool:
        return self.__visible__

    @visible.setter
    def visible(self, visible: bool) -> None:
        self.__visible__ = bool(visible)

    @property
    def name(self) -> str:
        return self.__game_name__

    @property
    def display_name(self) -> str:
        return self.__game_display_name__

    @display_name.setter
    def display_name(self, name: str) -> None:
        assert isinstance(name, str), 'Type error'
        assert 4 <= len(name) <= 64, 'Name length error'
        self.__game_display_name__ = str(name)
        MyGlobalServerStorage.STORAGE.rename_game(self.__game_name__, Util.to_functional_name(self.__game_display_name__))

    @property
    def url(self) -> str:
        return self.__game_url__

    @url.setter
    def url(self, url: str) -> None:
        assert isinstance(url, str), 'Type error'
        self.__game_url__ = None if url is None or len(str(url)) == 0 else str(url)

    @property
    def icon_image(self) -> PIL.Image.Image | None:
        if self.__icon_image__ is None:
            return None

        return MyGlobalServerStorage.STORAGE.MyImageLoader.MyIconStorage.get_image(self.__icon_image__)

    @icon_image.setter
    def icon_image(self, image: PIL.Image.Image | int | None):
        if self.__icon_image__ is not None and image is None:
            MyGlobalServerStorage.STORAGE.MyImageLoader.MyIconStorage.del_image(self.__icon_image__)
            self.__icon_image__ = None
        elif image is not None:
            self.__icon_image__ = int(image) if isinstance(image, int) else MyGlobalServerStorage.STORAGE.MyImageLoader.MyIconStorage.set_image(self.__icon_image__, image)

    @property
    def background_image(self) -> PIL.Image.Image | None:
        if self.__background_image__ is None:
            return None

        return MyGlobalServerStorage.STORAGE.MyImageLoader.MyBackgroundStorage.get_image(self.__background_image__)

    @background_image.setter
    def background_image(self, image: PIL.Image.Image | int | None):
        if self.__background_image__ is not None and image is None:
            MyGlobalServerStorage.STORAGE.MyImageLoader.MyBackgroundStorage.del_image(self.__background_image__)
            self.__background_image__ = None
        elif image is not None:
            self.__background_image__ = int(image) if isinstance(image, int) else MyGlobalServerStorage.STORAGE.MyImageLoader.MyBackgroundStorage.set_image(self.__background_image__, image)


class MyProgramStorageInfo:
    def __init__(self, name: str, display_name: str, url: str | None, icon_image: int | None, visible: bool, width: int, height: int, program_type: Util.ProgramType):
        self.__program_name__: str = str(name)
        self.__program_display_name__: str = str(display_name)
        self.__url__: str | None = None if url is None else str(url)
        self.__image__: int | None = None if icon_image is None else int(icon_image)
        self.__visible__: bool = bool(visible)
        self.__dimensions__: tuple[int, int] = (int(width), int(height))
        self.__program_type__: Util.ProgramType = Util.ProgramType(program_type)

    def save(self) -> dict:
        return {
            'visible': self.__visible__,
            'display-name': self.__program_display_name__,
            'url': self.__url__,
            'icon-image': None if self.__image__ is None else self.__image__,
            'width': self.__dimensions__[0],
            'height': self.__dimensions__[1],
            'program-type': self.__program_type__.value
        }

    def send_dict(self) -> dict:
        return {
            'visible': self.__visible__,
            'display-name': self.__program_display_name__,
            'url': self.__url__,
            'icon-image': None if self.__image__ is None else str(self.__image__),
            'width': self.__dimensions__[0],
            'height': self.__dimensions__[1],
            'program-type': self.__program_type__.value
        }

    @property
    def visible(self) -> bool:
        return self.__visible__

    @visible.setter
    def visible(self, visible: bool) -> None:
        self.__visible__ = bool(visible)

    @property
    def name(self) -> str:
        return self.__program_name__

    @property
    def display_name(self) -> str:
        return self.__program_display_name__

    @display_name.setter
    def display_name(self, name: str) -> None:
        assert isinstance(name, str), 'Type error'
        assert 4 <= len(name) <= 64, 'Name length error'
        self.__program_display_name__ = str(name)
        MyGlobalServerStorage.STORAGE.rename_program(self.__program_name__, Util.to_functional_name(self.__program_display_name__))

    @property
    def url(self) -> str:
        return self.__url__

    @url.setter
    def url(self, url: str) -> None:
        assert url is None or isinstance(url, str), 'Type error'
        self.__url__ = None if url is None or len(str(url)) == 0 else str(url)

    @property
    def icon_image(self) -> PIL.Image.Image | None:
        if self.__image__ is None:
            return None

        return MyGlobalServerStorage.STORAGE.MyImageLoader.MyIconStorage.get_image(self.__image__)

    @icon_image.setter
    def icon_image(self, image: PIL.Image.Image | int | None):
        if self.__image__ is not None and image is None:
            MyGlobalServerStorage.STORAGE.MyImageLoader.MyIconStorage.del_image(self.__image__)
            self.__image__ = None
        elif image is not None:
            self.__image__ = int(image) if isinstance(image, int) else MyGlobalServerStorage.STORAGE.MyImageLoader.MyIconStorage.set_image(self.__image__, image)

    @property
    def dimensions(self) -> tuple[int, int]:
        return self.__dimensions__

    @dimensions.setter
    def dimensions(self, dimension: tuple[int | None, int | None]) -> None:
        width: int = self.__dimensions__[0] if dimension[0] is ... else 1 if dimension[0] is None else int(dimension[0])
        height: int = self.__dimensions__[1] if dimension[1] is ... else 1 if dimension[1] is None else int(dimension[1])
        self.__dimensions__ = (width, height)

    @property
    def program_type(self) -> Util.ProgramType:
        return self.__program_type__

    @program_type.setter
    def program_type(self, value: int | Util.ProgramType) -> None:
        self.__program_type__ = Util.ProgramType(value)


class MyContactStorageInfo:
    def __init__(self, name: str, display_name: str, content: str | None, contact_type: Util.ContactType, icon_image: int | None, visible: bool):
        self.__contact_name__: str = str(name)
        self.__contact_display_name__: str = str(display_name)
        self.__content__: str | None = None if content is None else str(content)
        self.__contact_type__: Util.ContactType = Util.ContactType(contact_type)
        self.__image__: int | None = None if icon_image is None else int(icon_image)
        self.__visible__: bool = bool(visible)

    def save(self) -> dict:
        return {
            'visible': self.__visible__,
            'display-name': self.__contact_display_name__,
            'contact-type': self.__contact_type__.value,
            'content': self.__content__,
            'icon-image': None if self.__image__ is None else self.__image__,
        }

    def send_dict(self) -> dict:
        return {
            'visible': self.__visible__,
            'display-name': self.__contact_display_name__,
            'url': self.url,
            'contact-type': self.__contact_type__.value,
            'content': self.__content__,
            'icon-image': None if self.__image__ is None else str(self.__image__),
        }

    @property
    def visible(self) -> bool:
        return self.__visible__

    @visible.setter
    def visible(self, visible: bool) -> None:
        self.__visible__ = bool(visible)

    @property
    def name(self) -> str:
        return self.__contact_name__

    @property
    def display_name(self) -> str:
        return self.__contact_display_name__

    @display_name.setter
    def display_name(self, name: str) -> None:
        assert isinstance(name, str), 'Type error'
        assert 4 <= len(name) <= 64, 'Name length error'
        self.__contact_display_name__ = str(name)
        MyGlobalServerStorage.STORAGE.rename_contact(self.__contact_name__, Util.to_functional_name(self.__contact_display_name__))

    @property
    def content(self) -> str:
        return self.__content__

    @content.setter
    def content(self, content: str | None) -> None:
        assert content is None or isinstance(content, str), 'Type error'
        self.__content__ = None if content is None or len(str(content)) == 0 else str(content)
        self.__contact_type__ = Util.ContactType.NONE if self.__content__ is None else self.__contact_type__

    @property
    def contact_type(self) -> Util.ContactType:
        return self.__contact_type__

    @contact_type.setter
    def contact_type(self, value: int | Util.ContactType) -> None:
        self.__contact_type__ = Util.ContactType(value)

    @property
    def icon_image(self) -> PIL.Image.Image | None:
        if self.__image__ is None:
            return None

        return MyGlobalServerStorage.STORAGE.MyImageLoader.MyIconStorage.get_image(self.__image__)

    @icon_image.setter
    def icon_image(self, image: PIL.Image.Image | int | None):
        if self.__image__ is not None and image is None:
            MyGlobalServerStorage.STORAGE.MyImageLoader.MyIconStorage.del_image(self.__image__)
            self.__image__ = None
        elif image is not None:
            self.__image__ = int(image) if isinstance(image, int) else MyGlobalServerStorage.STORAGE.MyImageLoader.MyIconStorage.set_image(self.__image__, image)

    @property
    def url(self) -> str | None:
        if self.__contact_type__ == Util.ContactType.NONE:
            return None
        elif self.__contact_type__ == Util.ContactType.URL:
            return self.__content__
        elif self.__contact_type__ == Util.ContactType.MAIL:
            return f'mailto:{self.__content__}'
        elif self.__contact_type__ == Util.ContactType.PHONE:
            return f'tel:{self.__content__}'
        else:
            raise ValueError(f'Unknown contact type: \'{self.__contact_type__}\'')


class MyGlobalServerStorage:
    STORAGE: MyGlobalServerStorage = None

    @classmethod
    def load(cls, path: str) -> MyGlobalServerStorage:
        file: FileSystem.File = FileSystem.File(path)
        storage: MyGlobalServerStorage = cls()

        if not file.exists():
            return storage

        try:
            with file.open('r') as f:
                data: dict = json.load(f)

            for game_name, game in data['game-storage'].items():
                game_item: MyGameStorageInfo = MyGameStorageInfo(game_name, game['display-name'], game['game-url'], game['icon-image'], game['background-image'], game['visible'] if 'visible' in game else True)

                for section_name, section in game['sections'].items():
                    if len(section) == 0:
                        continue

                    game_item.add_section(section_name, section['display-name'], section['background-image'] if 'background-image' in section else None, section['visible'] if 'visible' in section else False)

                    for child_name, child in section['children'].items():
                        game_item.add_child(section_name, child_name, child['display-name'], child['url'], child['icon-image'], section['visible'] if 'visible' in section else False)

                storage.__game_info__[game_name] = game_item

            for program_name, program in data['program-storage'].items():
                program_item: MyProgramStorageInfo = MyProgramStorageInfo(program_name, program['display-name'], program['url'], program['icon-image'], program['visible'], program['width'], program['height'], Util.ProgramType(program['program-type']))
                storage.__program_info__[program_name] = program_item

            for contact_name, contact in data['contact-storage'].items():
                contact_item: MyContactStorageInfo = MyContactStorageInfo(contact_name, contact['display-name'], contact['content'], Util.ContactType(contact['contact-type']), contact['icon-image'], contact['visible'])
                storage.__contact_info__[contact_name] = contact_item

        except Exception as err:
            raise IOError('Failed to load server data') from err

        return storage

    def __new__(cls, *args, **kwargs) -> MyGlobalServerStorage:
        if MyGlobalServerStorage.STORAGE is None:
            MyGlobalServerStorage.STORAGE = super().__new__(cls, *args, **kwargs)

        return MyGlobalServerStorage.STORAGE

    def __init__(self):
        self.__game_info__: dict[str, MyGameStorageInfo] = {}
        self.__program_info__: dict[str, MyProgramStorageInfo] = {}
        self.__contact_info__: dict[str, MyContactStorageInfo] = {}
        self.__images__: Image.MyImageLoader = Image.MyImageLoader('Data/images')

    def save(self, path: str) -> None:
        file: FileSystem.File = FileSystem.File(path)

        try:
            with file.open('w') as f:
                f.write(json.dumps({
                    'game-storage': {child.name: child.save() for child in self.__game_info__.values()},
                    'program-storage': {child.name: child.save() for child in self.__program_info__.values()},
                    'contact-storage': {child.name: child.save() for child in self.__contact_info__.values()},
                }, indent=4))
        except Exception as err:
            raise IOError('Failed to save server data') from err

    def send_dict(self, visible_only: bool = True) -> dict:
        return {
            'game-storage': {child.name: child.send_dict(visible_only) for child in self.__game_info__.values() if not visible_only or child.visible},
            'program-storage': {child.name: child.send_dict() for child in self.__program_info__.values() if not visible_only or child.visible},
            'contact-storage': {child.name: child.send_dict() for child in self.__contact_info__.values() if not visible_only or child.visible}
        }

    def del_game(self, name: str) -> None:
        if name in self.__game_info__:
            del self.__game_info__[name]

    def rename_game(self, old_name: str, new_name: str) -> None:
        if old_name in self.__game_info__ and old_name != new_name:
            game: MyGameStorageInfo = self.__game_info__[old_name]
            game.__game_name__ = new_name
            self.__game_info__[new_name] = game
            del self.__game_info__[old_name]

    def add_game(self, name: str) -> MyGameStorageInfo:
        assert name not in self.__game_info__
        game: MyGameStorageInfo = MyGameStorageInfo(name, '', '', None, None, False)
        self.__game_info__[name] = game
        return game

    def get_game(self, name: str) -> MyGameStorageInfo | None:
        return self.__game_info__[name] if name in self.__game_info__ else None

    def del_program(self, name: str) -> None:
        if name in self.__program_info__:
            del self.__program_info__[name]

    def rename_program(self, old_name: str, new_name: str) -> None:
        if old_name in self.__program_info__ and old_name != new_name:
            program: MyProgramStorageInfo = self.__program_info__[old_name]
            program.__program_name__ = new_name
            self.__program_info__[new_name] = program
            del self.__program_info__[old_name]

    def add_program(self, name: str) -> MyProgramStorageInfo:
        assert name not in self.__program_info__
        program: MyProgramStorageInfo = MyProgramStorageInfo(name, '', None, None, False, 1, 1, Util.ProgramType.PROGRAM)
        self.__program_info__[name] = program
        return program

    def get_program(self, name: str) -> MyProgramStorageInfo | None:
        return self.__program_info__[name] if name in self.__program_info__ else None

    def del_contact(self, name: str) -> None:
        if name in self.__contact_info__:
            del self.__contact_info__[name]

    def rename_contact(self, old_name: str, new_name: str) -> None:
        if old_name in self.__contact_info__ and old_name != new_name:
            contact: MyContactStorageInfo = self.__contact_info__[old_name]
            contact.__contact_name__ = new_name
            self.__contact_info__[new_name] = contact
            del self.__contact_info__[old_name]

    def add_contact(self, name: str) -> MyContactStorageInfo:
        assert name not in self.__program_info__
        contact: MyContactStorageInfo = MyContactStorageInfo(name, '', None, Util.ContactType.NONE, None, False)
        self.__contact_info__[name] = contact
        return contact

    def get_contact(self, name: str) -> MyContactStorageInfo | None:
        return self.__contact_info__[name] if name in self.__contact_info__ else None

    @property
    def MyImageLoader(self) -> Image.MyImageLoader:
        return self.__images__
