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
    $.postJSON("/listDevices", function(data) {
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
}

function custom_build_device_card(dev,comment) {
    if ( dev != comment ) {
        comment = dev + ": " + comment
    }
    setTimeout (function() { custom_build_device_content(dev,comment); }, 500+Math.floor(Math.random() * 500));
    startcard = '<div class="mdl-cell mdl-cell--4-col" id="'+dev+'-card"><div> </div>'
    endcard = '</div>';
    return startcard + endcard;
}
function custom_build_device_content(dev,comment) {
    setTimeout (function() { custom_build_device_content(dev,comment); }, 5000+Math.floor(Math.random() * 5000));

    extraclass = ''
    $.postJSON("/"+dev+"/listStatus", function(data) {
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
    innercard = '<div class="mdl-card mdl-shadow--2dp">'
        + '<div class="card-title"><b>'+comment+'</b></div>'
        + '<table class="card-interior">'
        + '<tr class="card-interior-row">'
        + '<td><img id="'+dev+'img" class="icon'
        + extraclass + '" src="/getIcon/'+dev+'.svg" /></td>'
        + '<td><table class="small data" id="'+ dev
        + '"> </table></td></tr><tr><td colspan="3">'
        + '</td></tr></table></div>'
    $('#'+dev+'-card').html(innercard);
}

