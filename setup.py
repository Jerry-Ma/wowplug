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
            'sphinx-automodapi'
        ]}
setup(
    setup_requires=["setuptools-git", 'setuptools-git-version'],
    name='wowplug',
    version_format='0.0.dev{commitcount}+{gitsha}',
    description='An addon manager for WOW',
    long_description=long_description,
    author='Jerry Ma',
    author_email='jerry.ma.nk@gmail.com',
    url='https://github.com/Jerry-Ma/wowplug',
    license='BSD',
    classifiers=[
      'Development Status :: 3 - Alpha',
      'Intended Audience :: Developers',
      'Programming Language :: Python :: 3',
    ],
    keywords='',
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
