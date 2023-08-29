import sys

sys.path.append("..")
from materials.text import text_content


class Setup:
    def __init__(self):
        print(text_content.setup_header)
        is_correct = 1
        if is_correct:
            is_correct *= self.validate_modules()
        if is_correct:
            is_correct *= self.validate_key()
        self.is_correct = is_correct
        if is_correct:
            print(text_content.setup_done)
        else:
            print(text_content.setup_fail)

    def validate_modules(self):
        print(text_content.checking_modules)
        is_correct = 1
        try:
            import aiogram
        except:
            is_correct = 0
        if is_correct:
            print(text_content.success)
        else:
            print(text_content.fail)
            print(text_content.install_modules)
        return is_correct

    def validate_key(self):
        def write_key_to_file(key):
            key_file = open(text_content.key_path, "w")
            key_file.write(key)
            key_file.close()

        print(text_content.chacking_key)
        is_correct = 1
        try:
            key_file = open(text_content.key_path, "r")
            self.api_key = key_file.read().removesuffix("\n")
            key_file.close()
        except:
            print(text_content.fail)
            self.api_key = input(text_content.insert_api_key)
            write_key_to_file(self.api_key)
        try:

            async def test_key(key):
                bot = Bot(token=key, parse_mode=ParseMode.MARKDOWN)
                await bot.close()

            from aiogram import Bot
            from aiogram.enums.parse_mode import ParseMode

            test_key(self.api_key)
        except:
            print(text_content.incorrect_token)
            write_key_to_file(self.api_key)
            is_correct = 0

        if is_correct:
            print(text_content.success)
        else:
            print(text_content.fail)
        return is_correct

    def __str__(self) -> str:
        repr = text_content.setup_status
        if self.is_correct:
            repr += text_content.success + "\n"
            repr += text_content.api_key_is + self.api_key
        else:
            repr += text_content.fail + "\n"
            repr += text_content.try_setup
        return repr


if __name__ == "__main__":
    setup = Setup()
    print(setup)
