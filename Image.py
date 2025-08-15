import PIL.Image
import uuid

import CustomMethodsVI.FileSystem as FileSystem


class MyImageLoader:
    class MyImageContainer:
        def __init__(self, path: FileSystem.Directory, image_size: tuple[int, int] | None):
            assert isinstance(path, FileSystem.Directory), 'Not a directory'
            assert image_size is None or (isinstance(image_size, tuple) and len(image_size) == 2 and all(isinstance(x, int) for x in image_size)), 'Invalid size limit'

            self.__dirpath__: FileSystem.Directory = path
            self.__image_size__: tuple[int, int] | None = image_size

            if not self.__dirpath__.exists():
                self.__dirpath__.create()

        def __delitem__(self, image_id: int) -> None:
            self.del_image(image_id)

        def __setitem__(self, image_id: int, image: PIL.Image.Image) -> None:
            self.set_image(image_id, image)

        def __getitem__(self, image_id: int) -> PIL.Image.Image | None:
            return self.get_image(image_id)

        def del_image(self, image_id: int) -> None:
            assert isinstance(image_id, int)
            self.__dirpath__.delfile(f'{image_id}.jpg')

        def set_image(self, image_id: int | None, image: PIL.Image.Image) -> int:
            assert image_id is None or isinstance(image_id, int), 'Invalid image ID'
            assert isinstance(image, PIL.Image.Image), 'Not an image'

            if image_id is None:
                uid: uuid.UUID = uuid.uuid4()

                while self.__dirpath__.file(f'{int(uid.int)}.jpg').exists():
                    uid = uuid.uuid4()

                image_id = uid.int

            image = self.convert_image(image)
            image.save(self.__dirpath__.file(f'{int(image_id)}.jpg').filepath(), 'JPEG')
            return image_id

        def get_image(self, image_id: int) -> PIL.Image.Image | None:
            assert isinstance(image_id, int), 'Invalid image ID'

            file: FileSystem.File = self.__dirpath__.file(f'{int(image_id)}.jpg')

            if not file.exists() or file.extension() != 'jpg':
                return None

            image: PIL.Image.Image = PIL.Image.open(file.filepath(), 'r')
            return image if self.__image_size__ is None or image.size == self.__image_size__ else None

        def convert_image(self, image: PIL.Image.Image) -> PIL.Image.Image:
            assert isinstance(image, PIL.Image.Image), 'Not an image'

            if self.__image_size__ is not None:
                width, height = image.size
                scale: float = min(self.__image_size__[0] / width, self.__image_size__[1] / height)
                width = round(width * scale)
                height = round(height * scale)
                image = image.resize((width, height))
                x: int = max(0, round((self.__image_size__[0] - width) / 2))
                y: int = max(0, round((self.__image_size__[1] - height) / 2))
                blackbox: PIL.Image.Image = PIL.Image.new('RGB', self.__image_size__, 0x000000)
                blackbox.paste(image, (x, y))
                return blackbox

            return image.convert('RGB')

        def image_file(self, image_id: int) -> FileSystem.File | None:
            assert isinstance(image_id, int), 'Invalid image ID'
            file: FileSystem.File = self.__dirpath__.file(f'{int(image_id)}.jpg')
            return None if not file.exists() or file.extension() != 'jpg' else file

        @property
        def dir(self) -> FileSystem.Directory:
            return self.__dirpath__

    def __init__(self, image_dir: str) -> None:
        self.__dirpath__: FileSystem.Directory = FileSystem.Directory(image_dir)

        if not self.__dirpath__.exists():
            self.__dirpath__.create()

        self.__icon_storage__: MyImageLoader.MyImageContainer = MyImageLoader.MyImageContainer(self.__dirpath__.cd('icons'), (512, 512))
        self.__background_storage__: MyImageLoader.MyImageContainer = MyImageLoader.MyImageContainer(self.__dirpath__.cd('backgrounds'), (4096, 2048))
        self.__general_storage__: MyImageLoader.MyImageContainer = MyImageLoader.MyImageContainer(self.__dirpath__.cd('generic'), None)

    @property
    def MyIconStorage(self) -> MyImageContainer:
        return self.__icon_storage__

    @property
    def MyBackgroundStorage(self) -> MyImageContainer:
        return self.__background_storage__

    @property
    def MyGenericStorage(self) -> MyImageContainer:
        return self.__general_storage__
