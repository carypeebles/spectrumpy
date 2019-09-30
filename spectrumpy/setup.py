from setuptools import Extension, find_packages, setup

setup(name='spectrumpy',
      version='0.1',
      description='Client integration of Pitney Bowes Spectrum Technology Platform for Python',
      long_description=open("README.rst", encoding="utf-8").read(),
      url='https://github.com/carypeebles/spectrumpy',
      author='Cary Peebles',
      author_email='cary.peebles@pb.com',
      license='MIT',
      packages=find_packages("src"),
      package_dir={"": "src"},
      include_package_data=True,
      install_requires=[
            'requests',
            'zeep',
            'lxml',
            'configparser',
            'datetime'
      ],
      zip_safe=False)
