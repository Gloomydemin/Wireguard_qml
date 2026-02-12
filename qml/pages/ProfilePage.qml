import QtQuick 2.0
import QtQuick.Layouts 1.12
import Qt.labs.settings 1.0
import Lomiri.Components 1.3 as UITK
import io.thp.pyotherside 1.3

import "../components"

UITK.Page {
    Toast { id: toast }

    property bool isEditing: false
    property bool isImported: false
    property string errorMsg
    property string profileName
    property string ipAddress
    property string privateKey
    property bool hasPrivateKey: false
    property string extraRoutes
    property string dnsServers
    property string interfaceName
    property string preUp
    property string postUp
    property string preDown
    property string postDown
    property string privateKeyMask: "*************************************"

    property variant peers: []

    Settings {
        id: settings
        property int interfaceNumber: 0
    }
    header: UITK.PageHeader {
        id: header
        title: isEditing ? i18n.tr("Edit profile %1").arg(profileName) : i18n.tr("Create a new profile")
    }

    Flickable {
        id: flick
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.top: header.bottom
        anchors.topMargin: units.gu(2)
        contentHeight: col.height
        contentWidth: width

        Column {
            id: col
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.left: parent.left
            spacing: units.gu(1.5)

            Column {
                anchors.right: parent.right
                anchors.left: parent.left
                spacing: units.gu(1.5)
                MyTextField {
                    visible: !isEditing
                    title: i18n.tr("Profile name")
                    text: profileName
                    enabled: !isEditing
                    onChanged: {
                        errorMsg = ''
                        profileName = text
                    }
                }

                MyTextField {
                    id: privateKeyField
                    title: i18n.tr("Private Key")
                    placeholder: (isEditing && hasPrivateKey && (!privateKey || privateKey.length === 0))
                                 ? privateKeyMask
                                 : "a2VlcCB0aGlzIHNlY3JldAo="
                    text: privateKey
                    onChanged: {
                        errorMsg = ''
                        privateKey = text
                    }
                    control: RowLayout {
                        UITK.Button {
                            id: genKey
                            text: i18n.tr("Generate")
                            onClicked: {
                                privateKey = python.call_sync('vpn.instance.genkey', [])
                            }
                        }
                        UITK.Button {
                            text: i18n.tr("Copy pubkey")
                            enabled: privateKey
                            onClicked: {
                                const pubkey = python.call_sync(
                                                 'vpn.instance.genpubkey', [privateKey])
                                UITK.Clipboard.push(pubkey)
                                toast.show(i18n.tr("Public key copied to clipboard"))
                            }
                        }
                    }
                }
                MyTextField {
                    title: i18n.tr("IP address (with prefix length)")
                    text: ipAddress
                    placeholder: "10.0.0.14/24"
                    onChanged: {
                        errorMsg = ''
                        ipAddress = text
                    }
                }
                // TODO: Optional
                MyTextField {
                    title: i18n.tr("Extra routes")
                    text: extraRoutes
                    placeholder: "10.0.0.14/24"
                    onChanged: {
                        errorMsg = ''
                        extraRoutes = text
                    }
                }
                MyTextField {
                    title: i18n.tr("DNS")
                    text: dnsServers
                    placeholder: "10.0.0.1"
                    onChanged: {
                        errorMsg = ''
                        dnsServers = text
                    }
                }
                MyTextField {
                    title: i18n.tr("PreUp command")
                    text: preUp
                    placeholder: i18n.tr("Optional command to run before interface up")
                    onChanged: {
                        errorMsg = ''
                        preUp = text
                    }
                }
                MyTextField {
                    title: i18n.tr("PostUp command")
                    text: postUp
                    placeholder: i18n.tr("Optional command to run after interface up")
                    onChanged: {
                        errorMsg = ''
                        postUp = text
                    }
                }
                MyTextField {
                    title: i18n.tr("PreDown command")
                    text: preDown
                    placeholder: i18n.tr("Optional command to run before interface down")
                    onChanged: {
                        errorMsg = ''
                        preDown = text
                    }
                }
                MyTextField {
                    title: i18n.tr("PostDown command")
                    text: postDown
                    placeholder: i18n.tr("Optional command to run after interface down")
                    onChanged: {
                        errorMsg = ''
                        postDown = text
                    }
                }
            }

            Repeater {
                model: ListModel {
                    id: listmodel
                    dynamicRoles: true
                }
                delegate: Column {
                    id: peerCol
                    spacing: units.gu(1.5)
                    anchors.left: parent.left
                    anchors.right: parent.right
                    RowLayout {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.leftMargin: units.gu(2)
                        anchors.rightMargin: units.gu(2.1)
                        UITK.Label {
                            Layout.fillWidth: true
                            text: i18n.tr('Peer #%1').arg(index + 1)
                        }
                        UITK.Icon {
                            name: "delete"
                            width: units.gu(2)
                            height: units.gu(2)
                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    listmodel.remove(index)
                                }
                            }
                        }
                    }

                    MyTextField {
                        title: i18n.tr("Name")
                        text: name
                        onChanged: {
                            errorMsg = ''
                            name = text
                        }
                    }
                    MyTextField {
                        title: i18n.tr("Public key")
                        placeholder: "c29tZSBzaWxseSBzdHVmZgo="
                        text: key
                        onChanged: {
                            errorMsg = ''
                            key = text
                        }
                    }
                    MyTextField {
                        title: i18n.tr("Allowed IP prefixes")
                        text: allowedPrefixes
                        onChanged: {
                            errorMsg = ''
                            allowedPrefixes = text
                        }
                        placeholder: "10.0.0.1/32, 192.168.1.0/24"
                    }

                    MyTextField {
                        title: i18n.tr("Endpoint with port")
                        text: endpoint
                        onChanged: {
                            errorMsg = ''
                            endpoint = text
                        }
                        placeholder: "vpn.example.com:1234"
                    }

                    MyTextField {
                        title: i18n.tr("Preshared key")
                        placeholder: "c29tZSBzaWxseSBzdHVmZgo="
                        text: presharedKey
                        onChanged: {
                            errorMsg = ''
                            presharedKey = text
                        }
                    }
                }
            }

            UITK.Button {
                text: i18n.tr("Add peer")
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: units.gu(2)
                anchors.rightMargin: units.gu(2)
                onClicked: {
                    listmodel.append({
                                         "name": '',
                                         "key": '',
                                         "allowedPrefixes": '',
                                         "endpoint": '',
                                         "presharedKey": ''
                                     })
                }
            }
            UITK.Label {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: units.gu(2)
                anchors.rightMargin: units.gu(2)
                wrapMode: Text.WordWrap
                visible: errorMsg
                text: errorMsg
                color: 'red'
            }

            UITK.Button {
                id: save
                text: i18n.tr("Save profile")
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottomMargin: units.gu(2)
                anchors.leftMargin: units.gu(2)
                anchors.rightMargin: units.gu(2)
                enabled: listmodel.count && profileName && ipAddress
                         && (privateKey || isEditing)
                onClicked: {
                    errorMsg = ''
                    let _peers = []
                    for (var i = 0; i < listmodel.count; i++) {
                        const p = listmodel.get(i)
                        _peers.push({
                                        "name": p.name,
                                        "key": p.key,
                                        "allowed_prefixes": p.allowedPrefixes,
                                        "endpoint": p.endpoint,
                                        "presharedKey": p.presharedKey
                                    })
                    }

                    python.call('vpn.instance.save_profile',
                                [profileName, ipAddress, privateKey, interfaceName, extraRoutes, dnsServers, preUp, postUp, preDown, postDown, _peers],
                                function (error) {
                                    if (!error) {
                                        if (!isEditing) {
                                            settings.interfaceNumber = settings.interfaceNumber + 1
                                        }
                                        stack.clear()
                                        stack.push(Qt.resolvedUrl(
                                                       "PickProfilePage.qml"))
                                        return
                                    } else {
                                        console.log(error);
                                        errorMsg = error;
                                    }
                                })
                }
            }
        }
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

    Component.onCompleted: {
        const peerList = normalizePeers(peers)
        for (var i = 0; i < peerList.length; i++) {
            const p = peerList[i]
            listmodel.append({
                                 "name": p.name,
                                 "key": p.key,
                                 "allowedPrefixes": p.allowed_prefixes,
                                 "endpoint": p.endpoint,
                                 "presharedKey": p.presharedKey
                             })
        }
    }

    Python {
        id: python
        Component.onCompleted: {
            addImportPath(Qt.resolvedUrl('../../src/'))
            importModule('vpn', function () {
                python.call('vpn.instance.set_pwd', [root.pwd], function(result){});
            })
        }
    }
}
