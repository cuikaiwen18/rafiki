if ! [ -z "$1" ]
then
    DOCS_DIR=$1
else
    DOCS_DIR=$RAFIKI_VERSION
fi 

pip3.6 install sphinx sphinx_rtd_theme
sphinx-build -b html . docs/$DOCS_DIR/