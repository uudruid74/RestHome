function custom_init() {
    custom_set_subtitle();
    custom_get_dash();
    custom_get_devices();
}

function custom_set_subtitle() {
    $.getJSON("/getHomeName", function(data) {
        $('#subtitle').html( data.ok );
    });
}

function custom_get_dash() {
    $.getJSON("/getCustomDash", function(data) {
        if (data.hasOwnProperty('ok')) {
        statusbar = '<div class="mdl-dash mdl-shadow--2dp">';
        statusbar += '    <div class="center"><b>' + $('#subtitle').html() + '</b></div>';
        statusbar += '    <div class="center">' + data.ok + '</div>';
        statusbar += '</div>';
        $('#customdash').html(statusbar);
        setTimeout(custom_get_dash,10000);
        }
    });
}
function custom_get_devices() {
    $.getJSON("/listDevices", function(data) {
        $('#custom-content').html('');
        if (data.hasOwnProperty('ok')) {
        Object.keys(data).forEach(function(key,index) {
            if (key != 'ok' && key != 'default') {
                ret = custom_build_device_card(key,data[key]);
                $('#custom-content').append(ret);
            }
        })
        }
    })
    .fail(function(hdr,textstatus,error) {
        console.log(textstatus);
        console.log(error);
    });
    setTimeout(custom_get_devices,15000);
}

function custom_build_device_card(dev,comment) {
    extraclass = ''
    $.getJSON("/"+dev+"/listStatus", function(data) {
        statusinfo = '';
        count = 0;
        if (data.hasOwnProperty('ok')) {
        Object.keys(data).forEach(function(key,index) {
            if (key != 'ok' && key != 'default') {
                count++;
                lastvalue = data[key];
                if (key == 'power' || key.toLowerCase() == dev.toLowerCase()) {
                    if (data[key] == '1') {
                        $('#'+dev+'img').addClass('poweron');
                    }
                    else if (data[key] == '0') {
                        $('#'+dev+'img').addClass('poweroff');
                    }
                }
                statusinfo += '<tr><td><b>' + key + '</b></td><td>' + data[key] + "</td></tr>\n";
            }
        });
        $('#' + dev).html(statusinfo);
        if (count == 1) {
            if (lastvalue == '0') {
                $('#'+dev+'img').addClass('poweroff');
            }
            else if (lastvalue == '1') {
                $('#'+dev+'img').addClass('poweron');
            }
        }
        }
    })
    .fail(function(hdr,textstatus,error) {
        console.log(textstatus);
        console.log(error);
    });
    if ( dev != comment ) {
        comment = dev + ": " + comment
    }
    startcard = '<div class="mdl-cell mdl-cell--4-col">'
    innercard = '<div class="mdl-card mdl-shadow--2dp">'
        + '<div class="center"><b>'+comment+'</b></div>'
        + '<table><tr><td><img id="'+dev+'img" class="icon'
        + extraclass + '" src="/getIcon/'+dev+'.svg" /></td>'
        + '<td><table class="small data" id="'+ dev
        + '"> </table></td></tr><tr><td colspan="3">'
        + '</td></tr></table></div>'
    endcard = '</div>';
    return startcard + innercard + endcard;
}

