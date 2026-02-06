import QtQuick 2.0
import QtQuick.Layouts 1.12
import Lomiri.Components 1.3 as UITK
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
    property color bgColor: appPalette ? appPalette.normal.background : "#f7f7f7"
    property color baseColor: appPalette ? appPalette.normal.base : "#ffffff"
    property color textColor: appPalette ? appPalette.normal.foregroundText : "#111111"
    property color tertiaryTextColor: appPalette ? appPalette.normal.backgroundTertiaryText : "#888888"

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

    // Импорт страницы с Content Hub
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
        importProgressModal.open()
        python.call('vpn.instance.import_conf', [filePath], function(result) {
            handleImportResult(result)
        })
    }

    function importConfText(confText, profileName, interfaceName) {
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
            importConfText(payload, null, null)
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
        toast.show(i18n.tr("Profile imported successfully"))

        populateProfiles(function() {
            if (!result.profiles || result.profiles.length === 0) {
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
    
    // Модальное окно для выбора способа добавления профиля
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
            radius: height / 2
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
                        text: i18n.tr("Файл конфигурации WireGuard")
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
                        text: i18n.tr("Сканировать QR-код")
                        font.pixelSize: units.gu(2)
                        font.bold: true
                        color: textColor
                    }
                    Text {
                        text: i18n.tr("Быстрый импорт из камеры")
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
                        text: i18n.tr("Создать вручную")
                        font.pixelSize: units.gu(2)
                        font.bold: true
                        color: textColor
                    }
                    Text {
                        text: i18n.tr("Заполнить параметры вручную")
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
            property var status: (c_status && typeof c_status === "object")
                                 ? c_status
                                 : ({ "init": false, "peers": [] })
            onClicked: {
                if (!status.init) {
                    python.call('vpn.instance._connect',
                                [profile_name, !settings.useUserspace],
                                function (error_msg) {
                                    if (error_msg) {
                                        toast.show('Failed:' + error_msg)
                                        return
                                    }
                                    toast.show(i18n.tr('Connecting..'))
                                    populateProfiles(function() {
                                        showStatus()
                                    })
                                })
                } else {
                    python.call('vpn.instance.interface.disconnect', [interface_name],
                                function () {
                                    toast.show(i18n.tr("Disconnected"))
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
                        connected: status.peers && status.peers.length > 0
                        size: 2
                    }
                }
                Item {
                    height: 1
                    anchors.left: parent.left
                    anchors.right: parent.right
                }

                Rectangle {
                    visible: status.init
                    height: 1
                    color: tertiaryTextColor
                    anchors.left: parent.left
                    anchors.right: parent.right
                }

                Repeater {
                    visible: status.init
                    model: status.peers ? status.peers : []
                    anchors.left: parent.left
                    anchors.right: parent.right
                    delegate: RowLayout {
                        property bool peerUp: status.init
                                              && status.peers
                                              && status.peers[index]
                                              && status.peers[index].up
                        anchors.left: parent.left
                        anchors.right: parent.right
                        Text {
                            Layout.fillWidth: true
                            color: peerUp ? textColor : tertiaryTextColor
                            text: peerName(c_status.peers[index].public_key,
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
                                text: toHuman(c_status.peers[index].rx)
                            }
                            UITK.Icon {
                                source: '../../assets/arrow_up.png'
                                height: parent.height
                                keyColor: 'black'
                                color: 'green'
                            }
                            Text {
                                color: textColor
                                text: toHuman(c_status.peers[index].tx)
                            }
                            Text {
                                color: textColor
                                text: ' - ' + ago(
                                          c_status.peers[index].latest_handshake)
                            }
                        }
                    }
                }
            }
        }
    }

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

    Timer {
    repeat: true
    interval: 3000
    running: listmodel.count > 0
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

    function populateProfiles(onDone) {
        python.call('vpn.instance.list_profiles', [], function (profiles) {
            listmodel.clear()
            for (var i = 0; i < profiles.length; i++) {
                profiles[i].init = false
                listmodel.append(profiles[i])
            }
            if (onDone) {
                onDone()
            }
        })
    }
    function showStatus() {
        python.call('vpn.instance.interface.current_status_by_interface', [],
                    function (all_status) {
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

                            let status = {
                                "init": false
                            }
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
                                status = copy
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
                python.call('vpn.instance.set_pwd', [root.pwd], function(result){});
                if (settings.useUserspace) {
                    python.call('vpn.instance.cleanup_userspace', [], function (err) {
                        if (err) {
                            console.log("cleanup_userspace:", err)
                        }
                        populateProfiles(function() {
                            if (listmodel.count > 0) {
                                showStatus()
                            }
                        })
                    })
                } else {
                    populateProfiles(function() {
                        if (listmodel.count > 0) {
                            showStatus()
                        }
                    })
                }
            })
        }
    }
}
