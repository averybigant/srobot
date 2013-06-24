from setuptools import setup
setup(
        name = "srobot",
        version = "0.1.0a",
        description = "A simple wrapper for mechanize for writting web bots or crawlers.", 
        author = "Yu Renbi",
        author_email = "averybigant@gmail.com",
        url = "https://github.com/averybigant/srobot",
        packages = ["srobot"],
        requires = ["mechanize(==0.2.6)", "beautifulsoup4(==4.0.5)"],
        license = "Simplified BSD License"
    )

