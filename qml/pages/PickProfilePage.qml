import QtQuick 2.0
import QtQuick.Layouts 1.12
import Lomiri.Components 1.3 as UITK
import Lomiri.Components.Popups 1.3 as Popups
import Lomiri.Content 1.3 as ContentHub
import io.thp.pyotherside 1.3
import Qt.labs.settings 1.0
import "../components"

UITK.Page {
    id: pickPage

    property bool hasActiveInterfaces: false
    property var appPalette: (typeof theme !== "undefined" && theme && theme.palette)
                             ? theme.palette
                             : ((typeof Theme !== "undefined" && Theme && Theme.palette)
                                ? Theme.palette
                                : ((UITK.Theme && UITK.Theme.palette)
                                   ? UITK.Theme.palette
                                   : null))
    property bool lastImportWasZip: false
    property color bgColor: appPalette ? appPalette.normal.background : "#f7f7f7"
    property color baseColor: appPalette ? appPalette.normal.base : "#ffffff"
    property color textColor: appPalette ? appPalette.normal.foregroundText : "#111111"
    property color tertiaryTextColor: appPalette ? appPalette.normal.backgroundTertiaryText : "#888888"
    property bool useUserspaceEffective: settings.useUserspace
    property string backendLabel: useUserspaceEffective
                                  ? i18n.tr("Backend: userspace (wireguard-go)")
                                  : i18n.tr("Backend: kernel module")

    Settings {
        id: settings
        property bool useUserspace: true
    }
    header: UITK.PageHeader {
        id: header
        title: i18n.tr("Wireguard")
        trailingActionBar.actions: [
            UITK.Action {
                iconName: "settings"
                onTriggered: {
                    stack.push(Qt.resolvedUrl("SettingsPage.qml"))
                }
            }
        ]
    }

    Rectangle {
        anchors.top: header.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: units.gu(3.2)
        color: "transparent"
        Row {
            anchors.left: parent.left
            anchors.leftMargin: units.gu(2)
            anchors.verticalCenter: parent.verticalCenter
            spacing: units.gu(0.6)
            Rectangle {
                radius: units.gu(1)
                color: settings.useUserspace ? "#ffd54f" : "#81c784"
                height: units.gu(2.4)
                width: text.implicitWidth + units.gu(2.4)
                anchors.verticalCenter: parent.verticalCenter
                Text {
                    id: text
                    anchors.centerIn: parent
                    color: "#000000"
                    font.pixelSize: units.gu(1.4)
                    text: backendLabel
                }
            }
        }
    }

    // Import page with Content Hub
    function openImportPage() {
        var importPage = stack.push(Qt.resolvedUrl("ImportPage.qml"), {
            "contentType": ContentHub.ContentType.Documents,
            "handler": ContentHub.ContentHandler.Source
        })
        
        importPage.importFinished.connect(function(filePath) {
            importConfPath(filePath)
        })
    }
    
    function importConfPath(filePath) {
        console.log("Importing file:", filePath)
        lastImportWasZip = filePath && filePath.toLowerCase().endsWith(".zip")
        importProgressModal.open()
        python.call('vpn.instance.import_conf', [filePath], function(result) {
            handleImportResult(result)
        })
    }

    function importConfText(confText, profileName, interfaceName) {
        lastImportWasZip = false
        var nameOverride = (profileName && profileName.length > 0) ? profileName : null
        var ifaceOverride = (interfaceName && interfaceName.length > 0) ? interfaceName : null
        importProgressModal.open()
        python.call('vpn.instance.import_conf_text',
                    [confText, nameOverride, ifaceOverride],
                    function(result) {
                        handleImportResult(result)
                    })
    }

    function openQrScanPage() {
        var qrPage = stack.push(Qt.resolvedUrl("QrScanPage.qml"))
        qrPage.qrDecoded.connect(function(payload) {
            openQrNameDialog(payload)
        })
    }

    // Ask user for profile name after QR decode
    function openQrNameDialog(qrText) {
        var dlg = Popups.PopupUtils.open(qrNameDialogComponent, pickPage, { qrText: qrText })
        dlg.accepted.connect(function(profileName) {
            importConfText(qrText, profileName, null)
        })
    }

    function handleImportResult(result) {
        importProgressModal.close()
        if (result.error) {
            console.log("Import error:", result.error)
            toast.show(i18n.tr("Import failed: ") + result.error)
            return
        }
        console.log("Import success:", result)
        var count = (result.profiles && result.profiles.length) ? result.profiles.length : 0
        toast.show(count > 1
                   ? i18n.tr("Imported %1 profiles").arg(count)
                   : i18n.tr("Profile imported successfully"))

        populateProfiles(function() {
            if (!result.profiles || result.profiles.length === 0) {
                return
            }
            // Для zip или множественного импорта остаёмся на списке
            if (lastImportWasZip || result.profiles.length !== 1) {
                return
            }
            const importedName = result.profiles[0]
            for (var i = 0; i < listmodel.count; i++) {
                const entry = listmodel.get(i)
                if (entry.profile_name === importedName) {
                    stack.push(Qt.resolvedUrl("ProfilePage.qml"), {
                        "isEditing": true,
                        "profileName": entry.profile_name,
                        "peers": entry.peers || [],
                        "ipAddress": entry.ip_address || "",
                        "privateKey": entry.private_key || "",
                        "extraRoutes": entry.extra_routes || "",
                        "dnsServers": entry.dns_servers || "",
                        "interfaceName": entry.interface_name || "wg" + i,
                        "isImported": true
                    })
                    break
                }
            }
        })
    }
    
    // Modal sheet to choose how to add a profile
Rectangle {
    id: addOptionsModal
    width: parent.width
    height: optionsColumn.implicitHeight + units.gu(4)
    color: bgColor
    y: parent.height
    z: 10
    
    property bool opened: false
    
    function open() {
        opened = true
        y = parent.height - height
        modalBackground.opacity = 0.6
    }
    
    function close() {
        opened = false
        y = parent.height
        modalBackground.opacity = 0
    }
    
    Rectangle {
        id: modalBackground
        anchors.fill: parent
        color: "black"
        opacity: 0
        z: -1
        
        Behavior on opacity {
            NumberAnimation { duration: 180 }
        }
        
        MouseArea {
            anchors.fill: parent
            onClicked: addOptionsModal.close()
        }
    }

    Behavior on y {
        NumberAnimation { duration: 180; easing.type: Easing.OutCubic }
    }
    
    Column {
        id: optionsColumn
        anchors.fill: parent
        anchors.margins: units.gu(2)
        spacing: units.gu(1.5)

        Rectangle {
            width: units.gu(4)
            height: units.gu(0.5)
            radius: height / 0.5
            color: tertiaryTextColor
            opacity: 0.6
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Rectangle {
            width: parent.width
            height: units.gu(7.5)
            radius: units.gu(1)
            color: baseColor
            border.color: "#e0e0e0"
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.margins: units.gu(1.5)
                spacing: units.gu(1.5)

                UITK.Icon {
                    width: units.gu(2.8)
                    height: width
                    name: "document-import"
                    color: textColor
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: units.gu(0.2)

                    Text {
                        text: i18n.tr("Import .conf/.zip")
                        font.pixelSize: units.gu(2)
                        font.bold: true
                        color: textColor
                    }
                    Text {
                        text: i18n.tr("WireGuard configuration file")
                        font.pixelSize: units.gu(1.4)
                        color: tertiaryTextColor
                    }
                }

                UITK.Icon {
                    width: units.gu(2.2)
                    height: width
                    name: "go-next"
                    color: tertiaryTextColor
                }
            }

            MouseArea {
                anchors.fill: parent
                onClicked: {
                    addOptionsModal.close()
                    openImportPage()
                }
            }
        }

        Rectangle {
            width: parent.width
            height: units.gu(7.5)
            radius: units.gu(1)
            color: baseColor
            border.color: "#e0e0e0"
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.margins: units.gu(1.5)
                spacing: units.gu(1.5)

                UITK.Icon {
                    width: units.gu(2.8)
                    height: width
                    name: "camera"
                    color: textColor
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: units.gu(0.2)

                    Text {
                        text: i18n.tr("Scan QR code")
                        font.pixelSize: units.gu(2)
                        font.bold: true
                        color: textColor
                    }
                    Text {
                        text: i18n.tr("Quick import from camera")
                        font.pixelSize: units.gu(1.4)
                        color: tertiaryTextColor
                    }
                }

                UITK.Icon {
                    width: units.gu(2.2)
                    height: width
                    name: "go-next"
                    color: tertiaryTextColor
                }
            }

            MouseArea {
                anchors.fill: parent
                onClicked: {
                    addOptionsModal.close()
                    openQrScanPage()
                }
            }
        }

        Rectangle {
            width: parent.width
            height: units.gu(7.5)
            radius: units.gu(1)
            color: baseColor
            border.color: "#e0e0e0"
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.margins: units.gu(1.5)
                spacing: units.gu(1.5)

                UITK.Icon {
                    width: units.gu(2.8)
                    height: width
                    name: "add"
                    color: textColor
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: units.gu(0.2)

                    Text {
                        text: i18n.tr("Create manually")
                        font.pixelSize: units.gu(2)
                        font.bold: true
                        color: textColor
                    }
                    Text {
                        text: i18n.tr("Fill parameters manually")
                        font.pixelSize: units.gu(1.4)
                        color: tertiaryTextColor
                    }
                }

                UITK.Icon {
                    width: units.gu(2.2)
                    height: width
                    name: "go-next"
                    color: tertiaryTextColor
                }
            }

            MouseArea {
                anchors.fill: parent
                onClicked: {
                    addOptionsModal.close()
                    stack.push(Qt.resolvedUrl("ProfilePage.qml"),
                               {interfaceName: "wg" + listmodel.count})
                }
            }
        }
    }
}

Component {
    id: qrNameDialogComponent
    Popups.Dialog {
        id: qrDialog
        property string qrText: ""

        signal accepted(string profileName)
        signal rejected()

        title: i18n.tr("Profile name")
        text: i18n.tr("Enter a name for the imported profile")

        UITK.TextField {
            id: qrProfileField
            placeholderText: i18n.tr("Profile name")
        }

        RowLayout {
            spacing: units.gu(1)
            UITK.Button {
                text: i18n.tr("Cancel")
                onClicked: {
                    qrDialog.rejected()
                    Popups.PopupUtils.close(qrDialog)
                }
            }
            UITK.Button {
                text: i18n.tr("Save")
                color: UITK.LomiriColors.green
                onClicked: {
                    var name = qrProfileField.text.trim()
                    if (!name || name.length === 0) {
                        toast.show(i18n.tr("Please enter a profile name"))
                        return
                    }
                    qrDialog.accepted(name)
                    Popups.PopupUtils.close(qrDialog)
                }
            }
        }
    }
}


// Модальное окно с индикатором загрузки
    Rectangle {
        id: importProgressModal
        width: parent.width
        height: units.gu(10)
        color: bgColor
        y: parent.height
        z: 20
        
        property bool opened: false
        
        function open() {
            opened = true
            y = parent.height - height
            modalBackground2.opacity = 0.6
        }
        
        function close() {
            opened = false
            y = parent.height
            modalBackground2.opacity = 0
        }
        
        Rectangle {
            id: modalBackground2
            anchors.fill: parent
            color: "black"
            opacity: 0
            z: -1
            
            Behavior on opacity {
                NumberAnimation { duration: 250 }
            }
        }
        
        Behavior on y {
            NumberAnimation { duration: 250; easing.type: Easing.OutCubic }
        }
        
        Column {
            anchors.centerIn: parent
            spacing: units.gu(2)
            
            UITK.ActivityIndicator {
                anchors.horizontalCenter: parent.horizontalCenter
                running: importProgressModal.opened
            }
            
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: i18n.tr("Importing profile...")
                color: textColor
                font.pixelSize: units.gu(1.5)
            }
        }
    }

    ListView {
        anchors.top: header.bottom
        anchors.topMargin: units.gu(3.2)
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.bottomMargin: units.gu(10)
        spacing: units.gu(0.1)

        id: lv
        model: ListModel {
            id: listmodel
            dynamicRoles: true
        }

        delegate: UITK.ListItem {
            height: col.height + col.anchors.topMargin + col.anchors.bottomMargin
            function statusObj() {
                return (c_status && typeof c_status === "object")
                        ? c_status
                        : ({ "init": false, "peers": [], "connecting": false })
            }
            property var status: statusObj()
            onClicked: {
                if (!listmodel || index < 0) {
                    return
                }
                var status = statusObj()
                if (!status.init) {
                    // визуально показать, что начали подключение
                    listmodel.setProperty(index, 'c_status', {
                                               init: true,
                                               connecting: true,
                                               peers: [],
                                               started: Date.now() / 1000
                                           })
                    python.call('vpn.instance._connect',
                                [profile_name, !settings.useUserspace],
                                function (error_msg) {
                                    if (error_msg) {
                                        listmodel.setProperty(index, 'c_status', {
                                                                   init: false,
                                                                   connecting: false,
                                                                   peers: []
                                                               })
                                        toast.show('Failed:' + error_msg)
                                        return
                                    }
                                    // сразу показать, что соединяемся/соединены; уточним после опроса
                                    listmodel.setProperty(index, 'c_status', {
                                                               init: true,
                                                               connecting: true,
                                                               peers: [],
                                                               started: Date.now() / 1000
                                                           })
                                    toast.show(i18n.tr('Connecting..'))
                                    statusKickoff.restart()
                                    showStatus()
                                })
                } else {
                    python.call('vpn.instance.interface.disconnect', [interface_name],
                                function () {
                                    toast.show(i18n.tr("Disconnected"))
                                    listmodel.setProperty(index, 'c_status', {
                                                               init: false,
                                                               connecting: false,
                                                               peers: []
                                                           })
                                    showStatus()
                                })
                }
            }

            leadingActions: UITK.ListItemActions {
                actions: [
                    UITK.Action {
                        iconName: 'delete'
                        onTriggered: {
                            python.call('vpn.instance.delete_profile', [profile_name],
                                        function (error) {
                                            if (error) {
                                                console.log(error)
                                                toast.show(i18n.tr('Failed:') + error)
                                            }
                                            else
                                            {
                                                toast.show(i18n.tr('Profile %1 deleted').arg(profile_name));
                                                // toast.show('Profile '+ profile_name +' deleted');
                                                listmodel.remove(index);
                                            }
                                        })
                        }
                    }
                ]
            }

            trailingActions: UITK.ListItemActions {
                actions: [
                    UITK.Action {
                        iconName: 'edit'
                        onTriggered: {
                            stack.push(Qt.resolvedUrl("ProfilePage.qml"), {
                                           "isEditing": true,
                                           "profileName": profile_name,
                                           "peers": peers,
                                           "ipAddress": ip_address,
                                           "privateKey": private_key,
                                           "extraRoutes": extra_routes,
                                           "dnsServers": dns_servers,
                                           "interfaceName": (!interface_name || interface_name.length == 0)
                                                            ? "wg" + index
                                                            : interface_name
                                       })
                        }
                    }
                ]
            }

            Column {
                id: col
                anchors.top: parent.top
                anchors.margins: units.gu(2)
                anchors.left: parent.left
                anchors.right: parent.right
                spacing: units.gu(1)

                RowLayout {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    Text {
                        Layout.fillWidth: true
                        id: prof_name
                        text: profile_name
                        font.pixelSize: units.gu(2.25)
                        font.bold: true
                        color: textColor
                    }
                    TunnelStatus {
                        id: ts
                        connected: isConnected(statusObj())
                        connecting: !!statusObj().connecting
                        size: 2
                    }
                }
                Item {
                    height: 1
                    anchors.left: parent.left
                    anchors.right: parent.right
                }

                Rectangle {
                    visible: !!(status && status.init)
                    height: 1
                    color: tertiaryTextColor
                    anchors.left: parent.left
                    anchors.right: parent.right
                }

                Repeater {
                    visible: !!(status && status.init)
                    model: status.peers ? status.peers : []
                    anchors.left: parent.left
                    anchors.right: parent.right
                    delegate: RowLayout {
                        property bool peerUp: !!(status && status.init
                                                  && status.peers
                                                  && status.peers[index]
                                                  && status.peers[index].up)
                        anchors.left: parent.left
                        anchors.right: parent.right
                        Text {
                            Layout.fillWidth: true
                            color: peerUp ? textColor : tertiaryTextColor
                            text: peerName(status.peers && status.peers[index] ? status.peers[index].public_key : "",
                                           peers)
                        }
                        Row {

                            visible: peerUp
                            UITK.Icon {
                                source: '../../assets/arrow_down.png'
                                height: parent.height
                                keyColor: 'black'
                                color: 'blue'
                            }

                            Text {
                                color: textColor
                                text: toHuman(status.peers && status.peers[index] ? status.peers[index].rx : 0)
                            }
                            UITK.Icon {
                                source: '../../assets/arrow_up.png'
                                height: parent.height
                                keyColor: 'black'
                                color: 'green'
                            }
                            Text {
                                color: textColor
                                text: toHuman(status.peers && status.peers[index] ? status.peers[index].tx : 0)
                            }
                            Text {
                                color: textColor
                                text: ' - ' + ago(
                                          status.peers && status.peers[index] ? status.peers[index].latest_handshake : 0)
                            }
                        }
                    }
                }
            }
        }
    }

    Timer {
        repeat: true
        interval: hasActiveInterfaces ? 1500 : 5000
        running: listmodel.count > 0
        onTriggered: showStatus()
    }

    Timer {
        id: statusKickoff
        repeat: false
        interval: 500
        onTriggered: showStatus()
    }


    function normalizePeers(source) {
        if (!source) {
            return []
        }
        if (source.get && source.count !== undefined) {
            var arr = []
            for (var i = 0; i < source.count; i++) {
                arr.push(source.get(i))
            }
            return arr
        }
        if (source.length !== undefined) {
            return source
        }
        return []
    }

    function peerName(pubkey, peers) {
        const peerList = normalizePeers(peers)
        for (var i = 0; i < peerList.length; i++) {
            const peer = peerList[i]
            if (peer.key === pubkey) {
                return peer.name
            }
        }
        return 'unknown peer'
    }
    function ago(ts) {
        const delta = (new Date().getTime()) / 1000 - ts
        if (delta > 86400) {
            return Math.round(delta / 86400) + 'd'
        }
        if (delta > 3600) {
            return Math.round(delta / 3600) + 'h'
        }
        if (delta > 60) {
            return Math.round(delta / 60) + 'm'
        }
        if (delta < 60) {
            return Math.round(delta) + 's'
        }
    }

    function toHuman(q) {
        if (!q) {
            return 0
        }

        const units = ['B', 'KB', 'MB', 'GB', 'TB']
        let i = 0
        while (q > 1024) {
            q = q / 1024
            i++
        }
        return Math.round(q, 1) + units[i]
    }

    function isConnected(status) {
        if (!status || !status.init) return false
        if (status.connecting) return false
        const peerList = normalizePeers(status.peers)
        for (var i = 0; i < peerList.length; i++) {
            if (peerList[i].up) {
                return true
            }
        }
        // если нет информации по пирами, но init=true, считаем подключено
        return peerList.length === 0 ? true : false
    }

    function populateProfiles(onDone) {
        python.call('vpn.instance.list_profiles', [], function (profiles) {
            // сортировка по имени
            if (!profiles || !profiles.sort) {
                profiles = []
            }
            profiles.sort(function(a, b) {
                return (a.profile_name || "").toLowerCase().localeCompare((b.profile_name || "").toLowerCase());
            });
            listmodel.clear()
            for (var i = 0; i < profiles.length; i++) {
                profiles[i].init = false
                profiles[i].connecting = false
                listmodel.append(profiles[i])
            }
            if (onDone) {
                onDone()
            }
        })
    }
    function showStatus() {
        if (!listmodel) return
        python.call('vpn.instance.interface.current_status_by_interface', [],
                    function (all_status) {
                        if (!listmodel) return
                        all_status = all_status || {}
                        hasActiveInterfaces = Object.keys(all_status).length > 0
                        const keys = Object.keys(all_status)
                        var byPriv = {}
                        for (var k = 0; k < keys.length; k++) {
                            const st = all_status[keys[k]]
                            if (st && st.my_privkey) {
                                byPriv[st.my_privkey] = st
                            }
                        }
                        for (var i = 0; i < listmodel.count; i++) {
                            const entry = listmodel.get(i)

                            let status = entry.c_status ? entry.c_status : { init: false, connecting: false, peers: [] }
                            var matched = null
                            if (entry.interface_name && all_status[entry.interface_name]) {
                                matched = all_status[entry.interface_name]
                            } else if (entry.private_key && byPriv[entry.private_key]) {
                                matched = byPriv[entry.private_key]
                            }
                            if (matched) {
                                var copy = {}
                                for (var prop in matched) {
                                    copy[prop] = matched[prop]
                                }
                                copy['init'] = true
                                copy['connecting'] = false
                                status = copy
                            } else {
                                // если долго висим в состоянии connecting без статуса — сбрасываем
                                if (status.connecting && status.started) {
                                    var elapsed = (Date.now() / 1000) - status.started
                                    if (elapsed > 12) {
                                        status = { init: false, connecting: false, peers: [] }
                                    }
                                } else if (!status.connecting) {
                                    status = { init: false, connecting: false, peers: [] }
                                }
                            }
                            listmodel.setProperty(i, 'c_status', status)
                        }
                    })
    }

    // Floating action button (bottom-right) for add actions
    Rectangle {
        id: fabShadow
        width: units.gu(6.6)
        height: width
        radius: width / 2
        color: "#000000"
        opacity: 0.25
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: units.gu(2.1)
        anchors.bottomMargin: units.gu(2.1)
        z: 20
    }

    Rectangle {
        id: fabButton
        width: units.gu(6)
        height: width
        radius: width / 2
        color: "#1e88e5"
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: units.gu(2.4)
        anchors.bottomMargin: units.gu(2.4)
        z: 21

        UITK.Icon {
            anchors.centerIn: parent
            name: "add"
            width: units.gu(2.6)
            height: width
            color: "white"
        }

        MouseArea {
            anchors.fill: parent
            onClicked: addOptionsModal.open()
        }
    }

    Python {
        id: python
        Component.onCompleted: {
            addImportPath(Qt.resolvedUrl('../../src/'))
            importModule('vpn', function () {
                // синхронизируем флаг сразу при загрузке
                settings.useUserspace = settings.useUserspace
                python.call('vpn.instance.set_pwd', [root.pwd], function(result){});
                // First show UI promptly, then clean up userspace in background
                populateProfiles(function() {
                    if (listmodel.count > 0) {
                        showStatus()
                    }
                })
                if (settings.useUserspace) {
                    python.call('vpn.instance.cleanup_userspace', [], function (err) {
                        if (err) {
                            console.log("cleanup_userspace:", err)
                        }
                        // refresh statuses after cleanup (non-blocking)
                        showStatus()
                    })
                }
            })
        }
    }

    // Keep local settings in sync with root (WizardPage may change them)
    Connections {
        target: (typeof root !== "undefined") ? root.settings : null
        function onUseUserspaceChanged() {
            settings.useUserspace = root.settings.useUserspace
        }
        function onCanUseKmodChanged() {
            settings.canUseKmod = root.settings.canUseKmod
        }
    }
}
