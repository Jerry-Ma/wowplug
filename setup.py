from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get some values from the setup.cfg
try:
    from ConfigParser import ConfigParser
except ImportError:
    from configparser import ConfigParser

conf = ConfigParser()
conf.read([path.join(here, 'setup.cfg')])
metadata = dict(conf.items('metadata'))

# Get the long description from the README file
with open(path.join(here, metadata.get(
        'description-file', 'README.md')), encoding='utf-8') as f:
    long_description = f.read()
    long_description_content_type = "text/plain; charset=UTF-8"

# Define entry points for command-line scripts
entry_points = {'console_scripts': []}

if conf.has_section('entry_points'):
    entry_point_list = conf.items('entry_points')
    for entry_point in entry_point_list:
        entry_points['console_scripts'].append('{0} = {1}'.format(
            entry_point[0], entry_point[1]))

install_requires = [s.strip() for s in metadata.get(
    'install_requires', '').split(',')],
extras_require = {
        'dev': [
            'sphinx',
            'sphinx_rtd_theme',
            'nose',
            'coverage',
            'pypi-publisher',
            'sphinx-automodapi',
            'sphinxcontrib-fulltoc',
        ]}
setup(
    setup_requires=["setuptools-git", 'setuptools-git-version'],
    version_format='{tag}.dev{commitcount}+{gitsha}',
    name=metadata['package_name'],
    description=metadata['description'],
    long_description=long_description,
    long_description_content_type=long_description_content_type,
    author=metadata['author'],
    author_email=metadata['author_email'],
    license=metadata['license'],
    url=metadata['url'],
    classifiers=[
      'Development Status :: 3 - Alpha',
      'Topic :: Games/Entertainment',
      'Intended Audience :: End Users/Desktop',
      'Programming Language :: Python :: 3',
    ],
    platforms='any',
    keywords=['game', 'utility'],
    packages=find_packages(exclude=['docs', 'tests*']),
    include_package_data=True,
    exclude_package_data={
        '': ['.gitignore', ],
        },
    install_requires=install_requires,
    extras_require=extras_require,
    entry_points=entry_points,
    zip_safe=False,
)
