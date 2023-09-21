PROJECT_DIRPATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

docker run \
    --rm \
    --workdir='/usr/src/myapp' \
    -v "${PROJECT_DIRPATH}:/usr/src/myapp" \
    python:3.8-bullseye bash -c "pip install -r requirements.txt;
                               pip3 install pyinstaller;
                               pyinstaller main.py \
                               --clean \
                               --distpath=dist/linux/ \
                               --name plan_wip_105 \
                               --onefile -y;
                               chown -R ${UID} dist; "