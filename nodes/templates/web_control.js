var ws_uri = "http://{{ base_url }}/{{ echo_ws_path }}";

function lag()
{
    var start = (new Date).getTime();
    ws.send(JSON.stringify({
        msg: "lag",
        start: start
    }));
}

function ws_event() {
    $("#websocket_state").empty();
    if (ws.readyState == SockJS.CONNECTING) {
        $("#websocket_state").append("SockJS state: connecting");
    }
    if (ws.readyState == SockJS.OPEN) {
        $("#websocket_state").append("SockJS state: opened");
    }
    if (ws.readyState == SockJS.CLOSING) {
        $("#websocket_state").append("SockJS state: closing");
    }
    if (ws.readyState == SockJS.CLOSED) {
        $("#websocket_state").append('SockJS state: closed, attempting reconnect...');
        window.setTimeout( reconnect, 1000 );
    }
}

function reconnect() {
    // global var
    ws = new SockJS(ws_uri);
    ws_event();
    ws.onopen = function() { ws_event(); }
    ws.onclose = function() { ws_event(); }
    ws.onerror = function()  { ws_event(); }

    ws.onmessage = function (evt) {
        // the only message we expect is the result of our lag test
        var msg = jQuery.parseJSON(evt.data);

        var start = msg.start;
        var stop = (new Date).getTime();
        var diff = stop - start;
        $("#output").empty();
        $("#output").append("lag: "+ diff + " msec" );
    };
};

window.onload = function() {
    var wsz = window.innerWidth;
    var hsz = wsz/2;
    var stage = new Kinetic.Stage("container", wsz, hsz);
    big_radius = hsz/2-4;
    button_state = [0, 0, 0, 0];

    var joyLayer = new Kinetic.Layer();
    var bgLayer = new Kinetic.Layer();
    joyCenterX = wsz/4;
    joyCenterY = hsz/2;

    joytip = new Kinetic.Circle({
        x: joyCenterX,
        y: joyCenterY,
        radius: wsz/25,
        fill: "#00D2FF",
        stroke: "black",
        strokeWidth: 2,
        draggable: true
    });

    cursor_style(joytip);


    joytip.on("mouseup touchend", function() {
        joytip.x = joyCenterX;
        joytip.y = joyCenterY;
        joyLayer.draw();
        emit_joy_pos();
    });

    function emit_joy_pos() {
        // slightly funky scaling to match ROS joystick node
        axes = [-(joytip.x-joyCenterX)/big_radius,
                -(joytip.y-joyCenterY)/big_radius]

        var ms = "joystick axes: " + axes;
        $("#output").empty();
        $("#output").append(ms);
        ws.send(JSON.stringify({
            msg: "joy",
            axes: axes,
            buttons: button_state
        }));
    }

    joytip.on("dragmove", function() {
        emit_joy_pos();
    });

    joyLayer.add(joytip);

    var bg = new Kinetic.Circle({
        x: joyCenterX,
        y: joyCenterY,
        radius: big_radius,
        stroke: "black",
        strokeWidth: 2,
    });
    bgLayer.add(bg);

    stage.add(bgLayer);
    stage.add(joyLayer);

    add_buttons();

    function add_buttons() {
        var buttonLayer = new Kinetic.Layer();

        var allBtnCenterX = wsz*3/4;
        var allBtnCenterY = hsz/2;
        var btnOffset = wsz/8;

        var cfg = { num: 0,
                    x: allBtnCenterX-btnOffset,
                    y: allBtnCenterY,
                    color: "red"
                  }
        add_button(cfg, buttonLayer);

        var cfg = { num: 1,
                    x: allBtnCenterX,
                    y: allBtnCenterY+btnOffset,
                    color: "yellow"
                  }
        add_button(cfg, buttonLayer);

        var cfg = { num: 2,
                    x: allBtnCenterX+btnOffset,
                    y: allBtnCenterY,
                    color: "green"
                  }
        add_button(cfg, buttonLayer);

        var cfg = { num: 3,
                    x: allBtnCenterX,
                    y: allBtnCenterY-btnOffset,
                    color: "blue"
                  }
        add_button(cfg, buttonLayer);

        stage.add(buttonLayer);
    }

    function add_button(cfg, buttonLayer) {
        var btnRadius = wsz/25;
        var btn = new Kinetic.Circle({
            x: cfg.x,
            y: cfg.y,
            radius: btnRadius,
            fill: cfg.color,
            stroke: "black",
            strokeWidth: 2,
        });
        buttonLayer.add(btn);
        cursor_style(btn);

        btn.on("mousedown touchstart", function() {
            button_state[cfg.num] = 1;
            btn.fill = "black";
            buttonLayer.draw();
            emit_joy_pos();
        });

        btn.on("mouseup touchend", function() {
            button_state[cfg.num] = 0;
            btn.fill = cfg.color;
            buttonLayer.draw();
            emit_joy_pos();
        });
    }

    function cursor_style( node ) {
        // add cursor styling
        node.on("mouseover", function(){
            document.body.style.cursor = "pointer";
        });
        node.on("mouseout", function(){
            document.body.style.cursor = "default";
        });
    }
};




$(document).ready(function(){
    $("#output").empty();
    $("#output").append("Thanks for visiting!");

    $("#lag_test").click(lag);

    reconnect();

});
