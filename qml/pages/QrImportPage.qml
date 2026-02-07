import QtQuick 2.0
import Lomiri.Components 1.3 as UITK
import Lomiri.Content 1.3 as ContentHub

UITK.Page {
    id: qrImportPage

    property int contentType: ContentHub.ContentType.Text
    property int handler: ContentHub.ContentHandler.Source

    signal importFinished(string payload, bool isFile)
    signal importCancelled()

    header: UITK.PageHeader {
        id: pageHeader
        title: i18n.tr("Scan QR via Barcode Reader")
        trailingActionBar.actions: [
            UITK.Action {
                iconName: "close"
                onTriggered: {
                    importCancelled()
                    pageStack.pop()
                }
            }
        ]
    }

    ContentHub.ContentPeerPicker {
        id: picker
        anchors {
            fill: parent
            topMargin: pageHeader.height
        }
        visible: true
        showTitle: false
        contentType: qrImportPage.contentType
        handler: qrImportPage.handler

        onPeerSelected: {
            console.log("Peer selected:", peer)

            if (!peer) {
                console.log("No peer selected")
                importCancelled()
                pageStack.pop()
                return
            }

            var selectedPeer = peer
            selectedPeer.selectionType = ContentHub.ContentTransfer.Single
            var transfer = selectedPeer.request()

            if (!transfer) {
                console.log("Failed to create transfer")
                importCancelled()
                pageStack.pop()
                return
            }

            if (transfer.state === ContentHub.ContentTransfer.Charged) {
                processTransfer(transfer)
            } else {
                var stateChangedHandler = function() {
                    if (transfer.state === ContentHub.ContentTransfer.Charged) {
                        processTransfer(transfer)
                        transfer.stateChanged.disconnect(stateChangedHandler)
                    } else if (transfer.state === ContentHub.ContentTransfer.Failed) {
                        console.log("Transfer failed")
                        importCancelled()
                        pageStack.pop()
                        transfer.stateChanged.disconnect(stateChangedHandler)
                    }
                }
                transfer.stateChanged.connect(stateChangedHandler)
            }
        }

        onCancelPressed: {
            console.log("QR import cancelled by user")
            importCancelled()
            pageStack.pop()
        }
    }

    function processTransfer(transfer) {
        if (!transfer.items || transfer.items.length === 0) {
            console.log("No items in transfer")
            importCancelled()
            pageStack.pop()
            return
        }

        var item = transfer.items[0]
        if (!item) {
            console.log("Invalid transfer item")
            importCancelled()
            pageStack.pop()
            return
        }

        var payload = ""
        var isFile = false

        if (item.text && item.text.length > 0) {
            payload = item.text
        } else if (item.data && item.data.length > 0) {
            payload = item.data
        } else if (item.url) {
            var filePath = item.url.toString()
            if (filePath.startsWith("file://")) {
                filePath = filePath.substring(7)
            }
            payload = filePath
            isFile = true
        }

        if (!payload || payload.length === 0) {
            console.log("Empty QR payload")
            importCancelled()
            pageStack.pop()
            return
        }

        importFinished(payload, isFile)

        Qt.callLater(function() {
            pageStack.pop()
        })
    }
}
