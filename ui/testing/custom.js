DevCache = {};
DevList = {};
RestrictDevs = {};

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
function custom_refresh() {
    console.log("Custom Refresh");
    $(".device").each(function(index,elem) {
        console.log(elem);
        custom_build_device_content(elem.id.substring(0,elem.id.lastIndexOf('-')),$(elem).find('.card-title').text());
    });
    setTimeout(custom_refresh, 3000);
}
function custom_init() {
    custom_roomlist();
    custom_set_subtitle();
    custom_get_devices();
    $( window ).on( 'hashchange', custom_get_devices );
    setTimeout(custom_refresh, 5000);
}
function custom_roomlist() {
    navbar = $('#navbar');
    navbar.html('<a class="mdl-navigation__link" href="#">Home</a>');
    $.postJSON("/listRooms",function(data) {
        if (data.hasOwnProperty('ok')) {
            Object.keys(data).forEach(function(key,index) {
                if ((key != "Home") && (key != "ok")) {
                    RestrictDevs['#'+key] = data[key].split(' ');
                    navbar.append('<a class="mdl-navigation__link" href="#'+key+'">'+key+'</a>');
                }
            });
        }
    });
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
        }
    });
}
function populate_dialog(dev,devcache,comment) {
    $('#dial-devname').html(dev);
    $('#dial-comment').html(comment);
    var formdata = '<form action="#">\n';
    // need to use the new getType here to allow for drop-down lists
    Object.keys(devcache).forEach(function(key,index) {
        id = dev+'-'+key;
        formdata += '<div class="mdl-textfield mdl-js-textfield mdl-textfield--floating-label">'+
            '<input class="mdl-textfield__input" type="text" id="'+id+'" value="'+devcache[key]+'">'+
            '<label class="mdl-textfield__label" for="'+id+'">'+key+'</label>'+
            '</div>\n'
    });
    formdata += "</form>";
    $('#dial-statuslist').html(formdata);
    componentHandler.upgradeElements(document.getElementById('dial-statuslist'));
    // add a handler such that we update the server on focus change using setStatus
}

function custom_get_devices() {
    $.postJSON("/listDevices", function(data) {
        $('#custom-content').html('<div id="customdash" class="mdl-cell mdl-cell--12-col mdl-cell--8-col-tablet mdl-cell--4-col-phone"> </div>');
        custom_get_dash();
        if (data.hasOwnProperty('ok')) {
            DevList = {};
            ImgList = [];
            DevCache = {};
            Object.keys(data).forEach(function(key,index) {
                if (key != "ok" && key != 'default') {
                    DevList[key] = data[key];
                    ImgList.push("/getIcon/"+key+".svg");
                }
            });
            preloadImages(ImgList,function() {
                Object.keys(data).forEach(function(key,index) {
                    if (key != 'ok' && key != 'default') {
                        if (window.location.hash) {
                            if (RestrictDevs[window.location.hash].indexOf(key) == -1) {
                                return;
                            }
                        }
                        ret = custom_build_device_card(key);
                        $('#custom-content').append(ret);
                        custom_build_device_content(key,data[key]);
                    }
                });
            });
        }
    });
}

function custom_build_device_card(dev) {
    var startcard = '<div class="device mdl-cell mdl-card mdl-shadow--2dp mdl-cell--4-col" id="'+dev+'-card"><div> </div>'
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
            custom_build_device_content(dev,comment);
        });
}

function device_reset(dev) {
    $('#'+dev+'-card').removeClass("device-on device-off light-on heat-on");
}
function device_on(dev,comment) {
    device_reset(dev);
    if (comment == null) {
        $('#'+dev+'-card').addClass('device-on');
        return;
    }
    teststr = comment.toLowerCase();
    $('#'+dev+'-img').removeClass("poweroff").addClass("poweron");
    if (teststr.indexOf('light') != -1) {
        $('#'+dev+'-card').addClass('light-on');
    } else if (teststr.indexOf('heat') != -1) {
        $('#'+dev+'-card').addClass('heat-on');
    } else $('#'+dev+'-card').addClass('device-on');
}
function device_off(dev) {
    device_reset(dev);
    $('#'+dev+'-img').removeClass("poweron").addClass("poweroff");
    $('#'+dev+'-card').addClass('device-off');
}
function preloadImages(urls, allImagesLoadedCallback){
    var loadedCounter = 0;
    var toBeLoadedNumber = urls.length;
    urls.forEach(function(url){
        preloadImage(url, function(){
            loadedCounter++;
            if(loadedCounter == toBeLoadedNumber) {
                setTimeout(allImagesLoadedCallback,500);
            }
        });
    });
    function preloadImage(url, anImageLoadedCallback){
        var img = new Image();
        img.onload = anImageLoadedCallback;
        img.src = url;
    }
}
function custom_build_device_content(dev,comment) {
    var clickkey = '';
    var clickstatus = '';
    var statusinfo = '';
    var changed = false;
    var innercard;

    if (!(dev in DevCache)) {
        if ( dev !== comment) {
            title = dev + ": " + comment;
        } else {
            title = dev;
        }
        innercard = '<div class="card-title"><b>'+title+'</b></div>'
            + '<table class="card-interior">'
            + '<tr class="card-interior-row">'
            + '<td><img id="'+dev+'-img" class="icon" '
            + 'src="/getIcon/'+dev+'.svg" /></td>'
            + '<td><table class="small data" id="'+ dev
            + '"> </table></td></tr><tr><td colspan="3">'
            + '</td></tr></table>';
        changed = true;
        DevCache[dev] = {}
    }
    $.postJSON("/"+dev+"/listStatus", function(data) {
        var count = 0;
        if (changed)
            $('#'+dev+'-card').html(innercard);
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
                            device_on(dev,comment)
                        }
                        else if (data[key] == '0') {
                            device_off(dev)
                        }
                        clickkey = key;
                        clickstatus = data[key];
                    }
                    if (count < 7) {
                        statusinfo += '<tr><td><b>' + key + '</b></td><td>' + data[key] + "</td></tr>\n";
                    } else if (count == 7) {
                        statusinfo += "<tr><td><b>&hellip;</b><td><td><b>&hellip;</b></td></tr>\n"
                    }
                }
            });
            if (changed) {
                $('#' + dev).html(statusinfo);
                $("#"+dev+"-img").unbind().on('click',function(event) {
                    clickimage(dev,clickkey,clickstatus,comment);
                });
                $("#"+dev).unbind().on('click',function(event) {
                    populate_dialog(dev,DevCache[dev],comment)
                    var dialog = document.querySelector('dialog');
                    if (! dialog.showModal) {
                        dialogPolyfill.registerDialog(dialog);
                    }
                    dialog.showModal();
                    dialog.querySelector('.close').addEventListener('click', function() {
                        dialog.close();
                    });
                });
            }
        }
    });
}

