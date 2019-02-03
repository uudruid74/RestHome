DevCache = {};
DevList = {};

$.postJSON = function(url, func)
{
    var sendInfo = {
            password: Cookies.get("password")
       };

    $.ajax({
            type: "POST",
            url: url,
            dataType: "json",
            processData: false,
            contentType: 'application/json',
            success: func,
            data: JSON.stringify(sendInfo)
       });
}
function custom_init() {
    custom_set_subtitle();
    custom_get_dash();
    custom_get_devices();
}
function custom_set_subtitle() {
    $.postJSON("/getHomeName", function(data) {
        if (data.hasOwnProperty('error')) {
            location.href = '/ui/access.html';
        }
        $('#subtitle').html( data.ok );
    });
}

function custom_get_dash() {
    $.postJSON("/getCustomDash", function(data) {
        if (data.hasOwnProperty('ok')) {
        var statusbar = '<div class="mdl-dash mdl-shadow--2dp">';
        statusbar += '    <div class="center"><b>' + $('#subtitle').html() + '</b></div>';
        statusbar += '    <div class="center">' + data.ok + '</div>';
        statusbar += '</div>';
        $('#customdash').html(statusbar);
        setTimeout(custom_get_dash,10000);
        }
    });
}

function custom_get_devices() {
    $.postJSON("/listDevices", function(data) {
        $('#custom-content').html('');
        if (data.hasOwnProperty('ok')) {
            DevList = {}
            Object.keys(data).forEach(function(key,index) {
                DevList[key] = data[key];
                if (key != 'ok' && key != 'default') {
                    ret = custom_build_device_card(key,data[key]);
                    $('#custom-content').append(ret);
                    custom_build_device_content(key,data[key],true);
                }
            })
        }
    })
}

function custom_build_device_card(dev,comment) {
    var comment;
    if ( dev != comment ) {
        comment = dev + ": " + comment
    }
    var startcard = '<div class="mdl-cell mdl-cell--4-col" id="'+dev+'-card"><div> </div>'
    var endcard = '</div>';
    return startcard + endcard;
}

function clickimage(dev,clickkey,oldstatus,comment) {
    console.log("Clicked on " + dev + " clickkey = " + clickkey);
    var url;
    if (clickkey == '') {
        return;
    }
    if (clickkey == 'power') {
        if (oldstatus == '1') {
            url = "/"+dev+"/sendCommand/poweroff";
        } else {
            url = "/"+dev+"/sendCommand/poweron";
        }
    } else if (clickkey == 'enabled') {
        if (oldstatus == '1') {
            url = "/"+dev+"/setStatus/enabled/0";
        } else {
            url = "/"+dev+"/setStatus/enabled/1";
        }
    } else {
        if (oldstatus == '1') {
            url = "/"+dev+"/sendCommand/"+clickkey+"off";
        } else {
            url = "/"+dev+"/sendCommand/"+clickkey+"on";
        }
    }
    $.postJSON(url, function() {
            custom_build_device_content(dev,comment,false);
        });

}

function custom_build_device_content(dev,comment,loop) {
    var clickkey = '';
    var clickstatus = '';
    var statusinfo = '';
    var changed = false;

    if (!(dev in DevCache)) {
        innercard = '<div class="mdl-card mdl-shadow--2dp">'
            + '<div class="card-title"><b>'+comment+'</b></div>'
            + '<table class="card-interior">'
            + '<tr class="card-interior-row">'
            + '<td><img id="'+dev+'img" class="icon" '
            + 'src="/getIcon/'+dev+'.svg" /></td>'
            + '<td><table class="small data" id="'+ dev
            + '"> </table></td></tr><tr><td colspan="3">'
            + '</td></tr></table></div>';
        $('#'+dev+'-card').html(innercard);
        changed = true;
        DevCache[dev] = {}
    }
    $.postJSON("/"+dev+"/listStatus", function(data) {
        var count = 0;
        if (data.hasOwnProperty('ok')) {
            Object.keys(data).forEach(function(key,index) {
                if (key != 'ok' && key != 'default') {
                    count++;
                    if (DevCache[dev][key] != data[key]) {
                        DevCache[dev][key] = data[key];
                        changed = true;
                    }
                    lastvalue = data[key];
                    lastkey = key;
                    if (key == 'power' || key == 'enabled' || key.toLowerCase() == dev.toLowerCase()) {
                        if (data[key] == '1') {
                            $('#'+dev+'img').removeClass('poweroff').addClass('poweron');
                        }
                        else if (data[key] == '0') {
                            $('#'+dev+'img').removeClass('poweron').addClass('poweroff');
                        }
                        clickkey = key;
                        clickstatus = data[key];
                    }
                    statusinfo += '<tr><td><b>' + key + '</b></td><td>' + data[key] + "</td></tr>\n";
                }
            });
            if (changed) {
                $('#' + dev).html(statusinfo);
                $("#"+dev+"img").on('click',function(event) {
                    clickimage(dev,clickkey,clickstatus,comment);
                    event.stopPropagation();
                });
            }
            if (count == 1) {
                clickkey = lastkey;
                clickstatus = lastvalue
                if (lastvalue == '0') {
                    $('#'+dev+'img').removeClass('poweron').addClass('poweroff');
                }
                else if (lastvalue == '1') {
                    $('#'+dev+'img').removeClass('poweroff').addClass('poweron');
                }
            }
        }
        if (loop) {
            setTimeout (function() {
                custom_build_device_content(dev,comment,true);
            }, 8000+Math.floor(Math.random() * 4000));
        }
    })
}

