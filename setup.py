from distutils.core import setup

setup(
    name = "popen",
    packages = ['popen'],
    version = "0.1.14",
    description = "A shell-like DSL front for subprocess.Popen",
    long_description = open('README.rst').read(),
    author = "philipbergen",
    author_email = "philipbergen at gmail com",
    url = 'https://github.com/philipbergen/popen',
    keywords = "bash shell popen".split(),
    classifiers=["Development Status :: 5 - Production/Stable",
                 "Environment :: Console",
                 "Intended Audience :: Developers",
                 "License :: OSI Approved :: MIT License",
                 "Operating System :: MacOS :: MacOS X",
                 "Operating System :: POSIX :: Linux",
                 "Programming Language :: Python",
                 "Programming Language :: Python :: 2.7",
                 "Topic :: Software Development"],
     package_data = {
         'popen': ['*.rst'],
     }
)

