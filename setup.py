from setuptools import setup, find_packages

setup(
    name="openreview-matcher",
    version="2.0.7",
    description="OpenReview matching library",
    url="https://github.com/openreview/openreview-matcher",
    author="Michael Spector",
    author_email="spector@cs.umass.edu",
    license="MIT",
    packages=["matcher"],
    python_requires=">=3.10",
    setup_requires=["cffi>=1.0.0"],
    cffi_modules=[
        "matcher/solvers/bvn_extension/bvn_extension_build.py:ffibuilder"
    ],
    install_requires=[
        "numpy==2.*",
        "openreview-py",
        "ortools==9.*",
        "pytest==9.*",
        "sortedcontainers==2.*",
        "Flask==3.1.3",
        "Werkzeug==3.1.9",
        "flask-cors==6.*",
        "cffi==2.*",
        "pre-commit==4.*",
        "celery==5.6.3",
        "redis==6.4.0",
        "MarkupSafe==3.*",
        "gunicorn==26.*",
        "flake8==7.*",
        "gurobipy",
        "kombu==5.*",
        "psutil",
        "scipy"
    ],
    extras_require={
        "full": ["flower"],
    },
    zip_safe=False,
)
