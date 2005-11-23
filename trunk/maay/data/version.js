// version = "0.2.3";
function checkNewRelease()
{
    v= current_version.split(".");
    current_ver =parseInt(v[0]);
    current_release = parseInt(v[1]);
    current_subrelease = parseInt(v[2]);

    v= version.split(".");
    new_ver =parseInt(v[0]);
    new_release = parseInt(v[1]);
    new_subrelease = parseInt(v[2]);

    if (new_ver < current_ver)
        return 0;

    if (new_ver == current_ver)
    {
            if (new_release < current_release)
                return 0;

            if (new_release == current_release)
                if (new_subrelease <= current_subrelease)
                    return 0;
    }
    newReleaseMessage = document.getElementById("newReleaseMessage");
    newReleaseMessage.innerHTML = 'Your version of MAAY is outdated. <a href="http://maay.netofpeers.net/wiki/index.php/Download"> Download the version ' + version + ' of MAAY !</a>'
    return 1;
}
