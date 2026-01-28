import QtQuick 2.0
import QtQuick.Layouts 1.12
import Lomiri.Components 1.3 as UITK
import Lomiri.Content 1.3 as ContentHub
import io.thp.pyotherside 1.3
import Qt.labs.settings 1.0

import "../components"

UITK.Page {
    id: root
    Settings {
        id: settings
        property bool useUserspace: true
    }
    
    header: UITK.PageHeader {
        id: header
        title: i18n.tr("Wireguard")
        trailingActionBar.actions: [
            UITK.Action {
                iconName: "add"
                onTriggered: {
                    addOptionsModal.open()
                }
            },
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
            handleFileImport(filePath)
        })
    }
    
    // Функция обработки импорта файла
    function handleFileImport(filePath) {
        console.log("Importing file:", filePath)
        
        // Показываем индикатор загрузки
        importProgressModal.open()
        
        // Импортируем файл через Python
        python.call('vpn.instance.import_config', [filePath], function(result) {
            importProgressModal.close()
            
            if (result.error) {
                console.log("Import error:", result.error)
                toast.show(i18n.tr("Import failed: ") + result.error)
            } else {
                console.log("Import success:", result)
                toast.show(i18n.tr("Profile imported successfully"))
                
                // Обновляем список профилей
                populateProfiles()
                
                // Если создан новый профиль, открываем его для редактирования
                if (result.profile_name) {
                    Qt.callLater(function() {
                        for (var i = 0; i < listmodel.count; i++) {
                            const entry = listmodel.get(i)
                            if (entry.profile_name === result.profile_name) {
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
            }
        })
    }
    
    // Модальное окно для выбора способа добавления профиля
    Rectangle {
        id: addOptionsModal
        width: parent.width
        height: 180
        color: theme.palette.normal.background
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
                NumberAnimation { duration: 200 }
            }
            
            MouseArea {
                anchors.fill: parent
                onClicked: addOptionsModal.close()
            }
        }
        
        Behavior on y {
            NumberAnimation { duration: 200; easing.type: Easing.OutCubic }
        }
        
        Column {
            anchors.fill: parent
            spacing: 0
            
            // Rectangle {
            //     id: modalHeader
            //     width: parent.width
            //     height: units.gu(6)
            //     color: theme.palette.normal.base
                
            //     Text {
            //         anchors.centerIn: parent
            //         text: i18n.tr("Add Profile")
            //         font.pixelSize: units.gu(2)
            //         font.bold: true
            //         color: theme.palette.normal.foregroundText
            //     }
                
            //     UITK.Icon {
            //         anchors.right: parent.right
            //         anchors.rightMargin: units.gu(2)
            //         anchors.verticalCenter: parent.verticalCenter
            //         height: units.gu(3)
            //         width: height
            //         name: "close"
            //         color: theme.palette.normal.foregroundText
                    
            //         MouseArea {
            //             anchors.fill: parent
            //             onClicked: addOptionsModal.close()
            //         }
            //     }
            // }
            
            Column {
                width: parent.width
                height: parent.height // - modalHeader.height
                spacing: 0
                
                // Кнопка 1: Import .conf/.zip
                Rectangle {
                    width: parent.width
                    height: units.gu(8)
                    color: "transparent"
                    
                    Rectangle {
                        anchors.fill: parent
                        color: theme.palette.normal.base
                        opacity: importMa.pressed ? 0.3 : 0
                    }
                    
                    Row {
                        anchors.right: parent.right
                        anchors.rightMargin: units.gu(2)
                        anchors.centerIn: parent
                        spacing: units.gu(2)
                        
                        UITK.Icon {
                            anchors.verticalCenter: parent.verticalCenter
                            height: units.gu(3)
                            width: height
                            name: "document-import"
                            color: theme.palette.normal.foregroundText
                        }
                        
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: i18n.tr("Import .conf/.zip")
                            font.pixelSize: units.gu(1.3)
                            color: theme.palette.normal.foregroundText
                        }
                    }
                    
                    MouseArea {
                        id: importMa
                        anchors.fill: parent
                        onClicked: {
                            addOptionsModal.close()
                            openImportPage()
                        }
                    }
                }
                
                Rectangle {
                    width: parent.width
                    height: 1
                    color: theme.palette.normal.backgroundTertiaryText
                }
                
                // Кнопка 2: QR Code
                Rectangle {
                    width: parent.width
                    height: units.gu(8)
                    color: "transparent"
                    
                    Rectangle {
                        anchors.fill: parent
                        color: theme.palette.normal.base
                        opacity: qrMa.pressed ? 0.3 : 0
                    }
                    
                    Row {
                        anchors.right: parent.right
                        anchors.rightMargin: units.gu(2)
                        anchors.centerIn: parent
                        spacing: units.gu(2)
                        
                        UITK.Icon {
                            anchors.verticalCenter: parent.verticalCenter
                            height: units.gu(3)
                            width: height
                            source: "../../assets/camera-qr-code.png"
                            color: theme.palette.normal.foregroundText
                        }
                        
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: i18n.tr("Scan QR Code")
                            font.pixelSize: units.gu(1.3)
                            color: theme.palette.normal.foregroundText
                        }
                    }
                    
                    MouseArea {
                        id: qrMa
                        anchors.fill: parent
                        onClicked: {
                            addOptionsModal.close()
                            console.log("QR Code clicked")
                        }
                    }
                }
                
                Rectangle {
                    width: parent.width
                    height: 1
                    color: theme.palette.normal.backgroundTertiaryText
                }
                
                // Кнопка 3: Create from scratch
                Rectangle {
                    width: parent.width
                    height: units.gu(8)
                    color: "transparent"
                    
                    Rectangle {
                        anchors.fill: parent
                        color: theme.palette.normal.base
                        opacity: createMa.pressed ? 0.3 : 0
                    }
                    
                    Row {
                        anchors.right: parent.right
                        anchors.rightMargin: units.gu(2)
                        anchors.centerIn: parent
                        spacing: units.gu(2)
                        
                        UITK.Icon {
                            anchors.verticalCenter: parent.verticalCenter
                            height: units.gu(3)
                            width: height
                            name: "add"
                            color: theme.palette.normal.foregroundText
                        }
                        
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: i18n.tr("Create from scratch")
                            font.pixelSize: units.gu(1.3)
                            color: theme.palette.normal.foregroundText
                        }
                    }
                    
                    MouseArea {
                        id: createMa
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
    }
    
    // Модальное окно с индикатором загрузки
    Rectangle {
        id: importProgressModal
        width: parent.width
        height: units.gu(10)
        color: theme.palette.normal.background
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
                color: theme.palette.normal.foregroundText
                font.pixelSize: units.gu(1.5)
            }
        }
    }
    
    // Остальной код остается прежним...
    ListView {
        anchors.top: header.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        spacing: units.gu(0.1)

        id: lv
        model: ListModel {
            id: listmodel
            dynamicRoles: true
        }

        delegate: UITK.ListItem {
            height: col.height + col.anchors.topMargin + col.anchors.bottomMargin
            onClicked: {
                if (!c_status.init) {
                    python.call('vpn.instance._connect',
                                [profile_name, !settings.useUserspace],
                                function (error_msg) {
                                    if (error_msg) {
                                        toast.show('Failed:' + error_msg)
                                        return
                                    }
                                    toast.show(i18n.tr('Connecting..'))
                                    showStatus()
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
                                           "interfaceName": interface_name.length == 0 ? "wg" + index : interface_name
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
                        color: theme.palette.normal.foregroundText
                    }
                    TunnelStatus {
                        id: ts
                        connected: !!c_status.peers
                        size: 2
                    }
                }
                Item {
                    height: 1
                    anchors.left: parent.left
                    anchors.right: parent.right
                }

                Rectangle {
                    visible: c_status && !!c_status.init
                    height: 1
                    color: theme.palette.normal.backgroundTertiaryText
                    anchors.left: parent.left
                    anchors.right: parent.right
                }

                Repeater {
                    visible: c_status && !!c_status.init
                    model: c_status.peers
                    anchors.left: parent.left
                    anchors.right: parent.right
                    delegate: RowLayout {
                        property bool peerUp: c_status.init
                                              && c_status.peers[index].up
                        anchors.left: parent.left
                        anchors.right: parent.right
                        Text {
                            Layout.fillWidth: true
                            color: peerUp ? theme.palette.normal.foregroundText : theme.palette.normal.backgroundTertiaryText
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
                                color: theme.palette.normal.foregroundText
                                text: toHuman(c_status.peers[index].rx)
                            }
                            UITK.Icon {
                                source: '../../assets/arrow_up.png'
                                height: parent.height
                                keyColor: 'black'
                                color: 'green'
                            }
                            Text {
                                color: theme.palette.normal.foregroundText
                                text: toHuman(c_status.peers[index].tx)
                            }
                            Text {
                                color: theme.palette.normal.foregroundText
                                text: ' - ' + ago(
                                          c_status.peers[index].latest_handshake)
                            }
                        }
                    }
                }
            }
        }
    }

    Timer {
        repeat: true
        interval: 3000  // Реже, раз в 3 сек
        running: listmodel.count > 0
        onTriggered: showStatus()
    }



    function peerName(pubkey, peers) {
        for (var i = 0; i < peers.count; i++) {
            const peer = peers.get(i)
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

    function populateProfiles() {
        python.call('vpn.instance.list_profiles', [], function (profiles) {
            listmodel.clear()
            for (var i = 0; i < profiles.length; i++) {
                profiles[i].init = false
                listmodel.append(profiles[i])
            }
        })
    }
    function showStatus() {
        python.call('vpn.instance.get_status', [],
                    function (all_status) {
                        const keys = Object.keys(all_status)
                        for (var i = 0; i < listmodel.count; i++) {
                            const entry = listmodel.get(i)

                            let status = {
                                "init": false
                            }
                            for (const idx in Object.keys(all_status)) {
                                const key = keys[idx]
                                const i_status = all_status[key]
                                if (entry.interface_name === key) {
                                    status = i_status
                                    status['init'] = true
                                    break
                                }
                            }
                            listmodel.setProperty(i, 'c_status', status)
                        }
                    })
    }

    Python {
        id: python
        Component.onCompleted: {
            addImportPath(Qt.resolvedUrl("../../src/"))
            importModule("vpn", function () {
                // 1. передать пароль
                python.call("vpn.instance.set_pwd", [root.pwd], function() {
                    // 2. загрузить профили
                    populateProfiles()
                    // 3. после этого можно запускать showStatus
                    Qt.callLater(function() {
                        if (listmodel.count > 0)
                            showStatus()
                    })
                })
            })
        }
    }



}