import os

def setup():
    print('* doing setup')

if __name__ == "__main__":
    setup()

if __name__ != "__main__":
    try: os.environ['BOT_SETUP_DONE']
    except:
        print('')
        setup()