lifecycle_folder="$SHARED_FOLDER_PATH/lifecycle"
on_logon_script="$lifecycle_folder/on-logon.sh"

if [ -f "$on_logon_script" ]; then
    chmod +x "$on_logon_script"
    source "$on_logon_script"
else
    echo "No on-logon script found in $lifecycle_folder"
fi
