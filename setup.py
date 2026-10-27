from setuptools import setup, find_packages

setup(
    name="openreview-matcher",
    version="2.0.9",
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
        "pytest>=9.0.3,<10",
        "sortedcontainers==2.*",
        "Flask==3.1.3",
        "Werkzeug==3.1.9",
        "flask-cors==6.*",
        "cffi==2.*",
        "pre-commit==4.*",
        "bullmq==3.4.3",
        "MarkupSafe==3.*",
        "gunicorn==26.*",
        "flake8==7.*",
        "gurobipy",
        "psutil",
        "scipy"
    ],
    zip_safe=False,
)
