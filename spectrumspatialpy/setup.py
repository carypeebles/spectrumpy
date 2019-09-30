from setuptools import find_packages, setup

setup(name='spectrumspatialpy',
      version='0.1',
      description='Client integration of Pitney Bowes Spectrum Spatial for Python',
      long_description=open("README.rst", encoding="utf-8").read(),
      url='https://github.com/carypeebles/spectrumspatialpy',
      author='Cary Peebles',
      author_email='cary.peebles@pb.com',
      license='MIT',
      packages=find_packages("src"),
      package_dir={"": "src"},
      install_requires=[
            'spectrum',
            'shapely',
            'pandas',
            'geopandas',
            'colour',
            'datetime'
      ],
      zip_safe=False)
