from pydantic import BaseSettings, SecretStr


class Settings(BaseSettings):
    # Желательно вместо str использовать SecretStr 
    # для конфиденциальных данных, например, токена бота
    bot_token: SecretStr = "6577349724:AAFhGJJVmqWvUVDsqlAOFwvSt29CiXYlvE8"



    # НЕ ПОЛУЧИЛОСЬ СДЕЛАТЬ КАК ПО ГАЙДУ ХЗ



    # Вложенный класс с дополнительными указаниями для настроек
    class Config:
        # Имя файла, откуда будут прочитаны данные 
        # (относительно текущей рабочей директории)
        env_file = '.env'
        # Кодировка читаемого файла
        env_file_encoding = 'utf-8'


# При импорте файла сразу создастся 
# и провалидируется объект конфига, 
# который можно далее импортировать из разных мест
config = Settings()