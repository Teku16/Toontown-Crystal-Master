from direct.directnotify import DirectNotifyGlobal
from direct.gui.DirectGui import *
from direct.task.Task import Task
from pandac.PandaModules import *
from toontown.distributed import ToontownDistrictStats
from toontown.hood import ZoneUtil
from toontown.shtiker import ShtikerPage
from toontown.coghq import CogDisguiseGlobals
from toontown.suit import SuitDNA
from toontown.suit import Suit
from toontown.toonbase import TTLocalizer
from toontown.toonbase import ToontownGlobals
from toontown.toontowngui import TTDialog


ICON_COLORS = (Vec4(0.863, 0.776, 0.769, 1.0), Vec4(0.749, 0.776, 0.824, 1.0),
               Vec4(0.749, 0.769, 0.749, 1.0), Vec4(0.843, 0.745, 0.745, 1.0))

POP_COLORS = (Vec4(0.4, 0.4, 1.0, 1.0), Vec4(0.4, 1.0, 0.4, 1.0),
              Vec4(1.0, 0.4, 0.4, 1.0))

def compareShardTuples(a, b):
    if a[1] < b[1]:
        return -1
    elif b[1] < a[1]:
        return 1
    else:
        return 0

def setupInvasionMarkerAny(node):
    pass

def setupInvasionMarker(node, invasionStatus):
    if node.find('**/*invasion-marker'):
        return

    markerNode = node.attachNewNode('invasion-marker')

    if invasionStatus == 5:
        setupInvasionMarkerAny(markerNode)
        return

    icons = loader.loadModel('phase_3/models/gui/cog_icons')

    if invasionStatus == 1:
        icon = icons.find('**/CorpIcon').copyTo(markerNode)
    elif invasionStatus == 2:
        icon = icons.find('**/LegalIcon').copyTo(markerNode)
    elif invasionStatus == 3:
        icon = icons.find('**/MoneyIcon').copyTo(markerNode)
    else:
        icon = icons.find('**/SalesIcon').copyTo(markerNode)

    icons.removeNode()

    icon.setColor(ICON_COLORS[invasionStatus - 1])
    icon.setPos(0.50, 0, 0.0125)
    icon.setScale(0.0535)

def removeInvasionMarker(node):
    markerNode = node.find('**/*invasion-marker')

    if not markerNode.isEmpty():
        markerNode.removeNode()


class ShardPage(ShtikerPage.ShtikerPage):
    notify = DirectNotifyGlobal.directNotify.newCategory('ShardPage')

    def __init__(self):
        ShtikerPage.ShtikerPage.__init__(self)
        self.shardButtonMap = {}
        self.shardButtons = []
        self.scrollList = None
        self.currentBTP = None
        self.currentBTL = None
        self.currentBTR = None
        self.currentBTI = None
        self.currentO = None
        self.textRolloverColor = Vec4(1, 1, 0, 1)
        self.textDownColor = Vec4(0.5, 0.9, 1, 1)
        self.textDisabledColor = Vec4(0.4, 0.8, 0.4, 1)
        self.ShardInfoUpdateInterval = 5.0
        self.lowPop = config.GetInt('shard-low-pop', 150)
        self.midPop = config.GetInt('shard-mid-pop', 300)
        self.highPop = -1
        self.showPop = config.GetBool('show-population', 0)
        self.showTotalPop = config.GetBool('show-total-population', 0)
        self.noTeleport = config.GetBool('shard-page-disable', 0)
        self.shardGroups = None
        self.currentGroupJoined = None

    def load(self):
        main_text_scale = 0.06
        title_text_scale = 0.12
        self.title = DirectLabel(parent=self, relief=None, text=TTLocalizer.ShardPageTitle, text_scale=title_text_scale, textMayChange=0, pos=(0, 0, 0.6))
        helpText_ycoord = 0.403
        self.helpText = DirectLabel(parent=self, relief=None, text='', text_scale=main_text_scale, text_wordwrap=12, text_align=TextNode.ALeft, textMayChange=1, pos=(0.058, 0, helpText_ycoord))
        shardPop_ycoord = helpText_ycoord - 0.523
        totalPop_ycoord = shardPop_ycoord - 0.44
        self.districtInfo = NodePath('Selected-Shard-Info')
        self.districtInfo.reparentTo(self)
        self.totalPopulationText = DirectLabel(parent=self.districtInfo, relief=None, text=TTLocalizer.ShardPagePopulationTotal % 1, text_scale=main_text_scale, text_wordwrap=8, textMayChange=1, text_align=TextNode.ACenter, pos=(0.4247, 0, totalPop_ycoord))
        if self.showTotalPop:
            self.totalPopulationText.show()
        else:
            self.totalPopulationText.hide()
        self.gui = loader.loadModel('phase_3.5/models/gui/friendslist_gui')
        self.listXorigin = -0.02
        self.listFrameSizeX = 0.67
        self.listZorigin = -0.96
        self.listFrameSizeZ = 1.04
        self.arrowButtonScale = 1.3
        self.itemFrameXorigin = -0.247
        self.itemFrameZorigin = 0.365
        self.buttonXstart = self.itemFrameXorigin + 0.293
        self.regenerateScrollList()
        scrollTitle = DirectFrame(parent=self.scrollList, text=TTLocalizer.ShardPageScrollTitle, text_scale=main_text_scale, text_align=TextNode.ACenter, relief=None, pos=(self.buttonXstart, 0, self.itemFrameZorigin + 0.127))

    def firstLoadShard(self, buttonTuple):
        curShardTuples = base.cr.listActiveShards()
        curShardTuples.sort(compareShardTuples)
        actualShardId = base.localAvatar.defaultShard
        for i in xrange(len(curShardTuples)):
            shardId, name, pop, WVPop, invasionStatus = curShardTuples[i]
            if shardId == actualShardId:
                self.currentBTP = buttonTuple[0]
                self.currentBTL = buttonTuple[1]
                self.currentBTR = buttonTuple[2]
                self.currentBTI = buttonTuple[3]
                self.currentO = [pop, name, shardId]
                self.currentBTL['state'] = DGG.DISABLED
                self.currentBTR['state'] = DGG.DISABLED
                self.reloadRightBrain(pop, name, shardId, buttonTuple)

    def unload(self):
        self.gui.removeNode()
        del self.title
        self.scrollList.destroy()
        del self.scrollList
        del self.shardButtons
        taskMgr.remove('ShardPageUpdateTask-doLater')

        ShtikerPage.ShtikerPage.unload(self)

    def regenerateScrollList(self):
        selectedIndex = 0

        if self.scrollList:
            selectedIndex = self.scrollList.getSelectedIndex()
            for button in self.shardButtons:
                button.detachNode()
            self.scrollList.destroy()
            self.scrollList = None

        self.scrollList = DirectScrolledList(parent=self, relief=None, pos=(-0.51, 0, 0), incButton_image=(self.gui.find('**/FndsLst_ScrollUp'),
         self.gui.find('**/FndsLst_ScrollDN'),
         self.gui.find('**/FndsLst_ScrollUp_Rllvr'),
         self.gui.find('**/FndsLst_ScrollUp')), incButton_relief=None, incButton_scale=(self.arrowButtonScale, self.arrowButtonScale, -self.arrowButtonScale), incButton_pos=(self.buttonXstart + 0.005, 0, self.itemFrameZorigin - 1.000), incButton_image3_color=Vec4(1, 1, 1, 0.2), decButton_image=(self.gui.find('**/FndsLst_ScrollUp'),
         self.gui.find('**/FndsLst_ScrollDN'),
         self.gui.find('**/FndsLst_ScrollUp_Rllvr'),
         self.gui.find('**/FndsLst_ScrollUp')), decButton_relief=None, decButton_scale=(self.arrowButtonScale, self.arrowButtonScale, self.arrowButtonScale), decButton_pos=(self.buttonXstart, 0.0025, self.itemFrameZorigin + 0.130), decButton_image3_color=Vec4(1, 1, 1, 0.2), itemFrame_pos=(self.itemFrameXorigin, 0, self.itemFrameZorigin), itemFrame_scale=1.0, itemFrame_relief=DGG.SUNKEN, itemFrame_frameSize=(self.listXorigin,
         self.listXorigin + self.listFrameSizeX,
         self.listZorigin,
         self.listZorigin + self.listFrameSizeZ), itemFrame_frameColor=(0.85, 0.95, 1, 1), itemFrame_borderWidth=(0.01, 0.01), numItemsVisible=15, forceHeight=0.065, items=self.shardButtons)
        self.scrollList.scrollTo(selectedIndex)

    def askForShardInfoUpdate(self, task = None):
        ToontownDistrictStats.refresh('shardInfoUpdated')
        taskMgr.doMethodLater(self.ShardInfoUpdateInterval, self.askForShardInfoUpdate, 'ShardPageUpdateTask-doLater')
        return Task.done

    def makeShardButton(self, shardId, shardName, shardPop):
        shardButtonParent = DirectFrame()
        shardButtonL = DirectButton(parent=shardButtonParent, relief=None, text=shardName, text_scale=0.06, text_align=TextNode.ALeft, text_fg=Vec4(0, 0, 0, 1), text3_fg=self.textDisabledColor, text1_bg=self.textDownColor, text2_bg=self.textRolloverColor, textMayChange=0, command=self.reloadRightBrain)
        popText = str(shardPop)
        if popText is None:
            popText = ''
        model = loader.loadModel('phase_3.5/models/gui/matching_game_gui')
        button = model.find('**/minnieCircle')

        shardButtonR = DirectButton(parent=shardButtonParent, relief=None,
                                    image=button,
                                    image_scale=(0.3, 1, 0.3),
                                    image2_scale=(0.35, 1, 0.35),
                                    image_color=self.getPopColor(shardPop),
                                    pos=(0.58, 0, 0.0125),
                                    text=popText,
                                    text_scale=0.06,
                                    text_align=TextNode.ARight,
                                    text_pos=(-0.14, -0.0165), text_fg=Vec4(0, 0, 0, 1), text3_fg=self.textDisabledColor, text1_bg=self.textRolloverColor, text2_bg=self.textRolloverColor, textMayChange=1, command=self.reloadRightBrain)
        model.removeNode()
        button.removeNode()

        invasionMarker = NodePath('InvasionMarker-%s' % shardId)
        invasionMarker.reparentTo(shardButtonParent)

        buttonTuple = (shardButtonParent, shardButtonR, shardButtonL, invasionMarker)
        shardButtonL['extraArgs'] = extraArgs=[shardPop, shardName, shardId, buttonTuple]
        shardButtonR['extraArgs'] = extraArgs=[shardPop, shardName, shardId, buttonTuple]

        return buttonTuple

    def makeGroupButton(self, groupId, groupType):
        groupPop = len(base.cr.groupManager.getGroupPlayers(groupId))
        groupButtonParent = DirectFrame()
        groupButtonL = DirectButton(parent=groupButtonParent, relief=None, text=groupType, text_pos=(0.0, -0.0225), text_scale=0.06, text_align=TextNode.ALeft, text_fg=Vec4(0, 0, 0, 1), text3_fg=self.textDisabledColor, text1_bg=self.textDownColor, text2_bg=self.textRolloverColor, textMayChange=0, command=self.joinGroup)
        popText = str(groupPop)
        if popText is None:
            return
        model = loader.loadModel('phase_3.5/models/gui/matching_game_gui')
        button = model.find('**/minnieCircle')

        groupButtonR = DirectButton(parent=groupButtonParent, relief=None,
                                    image=button,
                                    image_scale=(0.3, 1, 0.3),
                                    image2_scale=(0.35, 1, 0.35),
                                    image_color=Vec4(0, 0.8, 0, 1),
                                    pos=(0.58, 0, -0.0125),
                                    text=popText,
                                    text_scale=0.055,
                                    text_align=TextNode.ACenter,
                                    text_pos=(-0.00575, -0.0125), text_fg=Vec4(0, 0, 0, 1), text3_fg=Vec4(0, 0, 0, 1), text1_bg=self.textRolloverColor, text2_bg=self.textRolloverColor, textMayChange=1)

        leaveButton = DirectButton(parent=groupButtonParent, relief=None,
                                   image=button,
                                   image_scale=(0.3, 1, 0.3),
                                   image2_scale=(0.35, 1, 0.35),
                                   image_color=Vec4(0, 0.8, 0, 1),
                                   pos=(0.50, 0, -0.0125),
                                   text='Leave',
                                   text_scale=0.055,
                                   text_align=TextNode.ACenter,
                                   text_pos=(-0.00575, -0.0125),
                                   text_fg=Vec4(0, 0, 0, 0),
                                   text2_fg=Vec4(0, 0, 0, 1),
                                   command=self.leaveGroup)

        leaveButton.hide()
        model.removeNode()
        button.removeNode()

        buttonTuple = (groupButtonParent, groupButtonR, groupButtonL, leaveButton)
        groupButtonL['extraArgs'] = [groupId, buttonTuple]
        leaveButton['extraArgs'] = [groupId, buttonTuple]
        return buttonTuple

    def removeRightBrain(self):
        self.districtInfo.find('**/*district-info').removeNode()

    def reloadRightBrain(self, shardPop, shardName, shardId, buttonTuple):
        self.currentRightBrain = (shardPop, shardName, shardId, buttonTuple)
        if self.districtInfo.find('**/*district-info'):
            self.removeRightBrain()
        if self.currentBTL:
            self.currentBTL['state'] = DGG.NORMAL
        if self.currentBTR:
            self.currentBTR['state'] = DGG.NORMAL
        popText = self.getPopText(shardPop)
        districtInfoNode = self.districtInfo.attachNewNode('district-info')
        self.districtStatusLabel = DirectLabel(parent=districtInfoNode, relief=None, pos=(0.4247, 0, 0.45), text=popText, text_scale=0.09, text_fg=Vec4(0, 0, 0, 1), textMayChange=1)
        pText = '%s Population: %s' % (shardName, str(shardPop))
        self.populationStatusLabel = DirectLabel(parent=districtInfoNode, relief=None, pos=(0.4247, 0, 0.38), text=pText, text_scale=0.04, text_fg=Vec4(0, 0, 0, 1), textMayChange=1)
        tText = 'Teleport to\n%s' % shardName
        tImage = loader.loadModel('phase_4/models/gui/purchase_gui')
        tImage.setSz(1.35)
        self.shardTeleportButton = DirectButton(parent=districtInfoNode, relief=None, pos=(0.4247, 0, 0.25), image=(tImage.find('**/PurchScrn_BTN_UP'), tImage.find('**/PurchScrn_BTN_DN'), tImage.find('**/PurchScrn_BTN_RLVR')), text=tText, text_scale=0.065, text_pos=(0.0, 0.015), text_fg=Vec4(0, 0, 0, 1), textMayChange=1, command=self.choseShard, extraArgs=[shardId])

        self.currentBTP = buttonTuple[0]
        self.currentBTL = buttonTuple[1]
        self.currentBTR = buttonTuple[2]
        self.currentBTI = buttonTuple[3]
        self.currentO = [shardPop, shardName, shardId]
        self.currentBTL['state'] = DGG.DISABLED
        self.currentBTR['state'] = DGG.DISABLED

        if shardId == self.getCurrentShardId():
            self.shardTeleportButton['state'] = DGG.DISABLED

        if self.shardGroups is not None:
            for button in self.shardGroups:
                button.detachNode()

        self.shardGroups = []

        for gid, gtype in base.cr.groupManager.id2type.items():
            btuple = self.makeGroupButton(gid, gtype)
            if base.cr.groupManager.isInGroup(base.localAvatar.doId, gid):
                btuple[1]['state'] = DGG.DISABLED
                btuple[2]['state'] = DGG.DISABLED
                btuple[3].show()
            self.shardGroups.append(btuple[0])

        self.districtGroups = DirectScrolledList(parent=districtInfoNode, relief=None,
                                                 pos=(0.38, 0, -0.34),
                                                 incButton_image=(self.gui.find('**/FndsLst_ScrollUp'),
                                                                  self.gui.find('**/FndsLst_ScrollDN'),
                                                                  self.gui.find('**/FndsLst_ScrollUp_Rllvr'),
                                                                  self.gui.find('**/FndsLst_ScrollUp')),
                                                 incButton_relief=None,
                                                 incButton_scale=(self.arrowButtonScale,
                                                                  self.arrowButtonScale,
                                                                  -self.arrowButtonScale),
                                                 incButton_pos=(self.buttonXstart + 0.005, 0, -0.125),
                                                 incButton_image3_color=Vec4(1, 1, 1, 0.2),
                                                 decButton_image=(self.gui.find('**/FndsLst_ScrollUp'),
                                                                  self.gui.find('**/FndsLst_ScrollDN'),
                                                                  self.gui.find('**/FndsLst_ScrollUp_Rllvr'),
                                                                  self.gui.find('**/FndsLst_ScrollUp')),
                                                 decButton_relief=None,
                                                 decButton_scale=(self.arrowButtonScale,
                                                                  self.arrowButtonScale,
                                                                  self.arrowButtonScale),
                                                 decButton_pos=(self.buttonXstart, 0.0025, 0.445),
                                                 decButton_image3_color=Vec4(1, 1, 1, 0.2),
                                                 itemFrame_pos=(self.itemFrameXorigin, 0, self.itemFrameZorigin),
                                                 itemFrame_scale=1.0,
                                                 itemFrame_relief=DGG.SUNKEN,
                                                 itemFrame_frameSize=(self.listXorigin,
                                                                      (self.listXorigin + self.listFrameSizeX),
                                                                      self.listZorigin/2.1,
                                                                      (self.listZorigin + self.listFrameSizeZ)/2.1),
                                                 itemFrame_frameColor=(0.85, 0.95, 1, 1),
                                                 itemFrame_borderWidth=(0.01, 0.01),
                                                 numItemsVisible=15,
                                                 forceHeight=0.065,
                                                 items=self.shardGroups)

    def joinGroup(self, groupId, buttonTuple):
        self.acceptOnce('confJoin', self.confirmJoinGroup, extraArgs=[groupId, buttonTuple])
        self.joinDialog = TTDialog.TTGlobalDialog(message='Would you like to join this group?', doneEvent='confJoin', style=4)

    def rejectGroup(self, reason, suitType=0):
        self.acceptOnce('remRjD', self.doneReject)
        if reason == 1:
            self.rejectDialog = TTDialog.TTGlobalDialog(message='You need more suit parts!', doneEvent='remRjD', style=1)
        elif reason == 2:
            if suitType == 0:
                meritType = 'Stock Options'
            elif suitType == 1:
                meritType = 'Merits'
            elif suitType == 2:
                meritType = 'Cogbucks'
            elif suitType == 3:
                meritType = 'Notices'
            self.rejectDialog = TTDialog.TTGlobalDialog(message='You need more %s!'%meritType, doneEvent='remRjD', style=1)
        elif reason == 3:
            self.rejectDialog = TTDialog.TTGlobalDialog(message='That group is full!', doneEvent='remRjD', style=1)
        elif reason == 4:
            self.rejectDialog = TTDialog.TTGlobalDialog(message='You\'re already in a group!', doneEvent='remRjD', style=1)
        elif reason == 5:
            self.rejectDialog = TTDialog.TTGlobalDialog(message='You can\'t leave the district while you\'re in a group!', doneEvent='remRjD', style=1)

    def doneReject(self):
        self.rejectDialog.cleanup()
        del self.rejectDialog

    def confirmJoinGroup(self, groupId, buttonTuple):
        doneStatus = self.joinDialog.doneStatus
        self.joinDialog.cleanup()
        del self.joinDialog
        if doneStatus is not 'ok':
            return
        for gid in base.cr.groupManager.id2type.keys():
            if base.cr.groupManager.isInGroup(base.localAvatar.doId, gid):
                self.rejectGroup(4)
                return
        #if len(base.cr.groupManager.getGroupPlayers(groupId)) >= 8:
        #    self.rejectGroup(3)
        #    return
        suitIdx = -1
        gids = {10000:0, 11000:1, 12000:2, 13000:3}
        suitIdx = gids.get(groupId)
        if suitIdx is not None:
            merits = base.localAvatar.cogMerits[suitIdx]
            if CogDisguiseGlobals.getTotalMerits(base.localAvatar, suitIdx) > merits:
                self.rejectGroup(2, suitIdx)
                return
            parts = base.localAvatar.getCogParts()
            if not CogDisguiseGlobals.isSuitComplete(parts, suitIdx):
                self.rejectGroup(1)
                return
        base.cr.groupManager.d_addPlayerToGroup(groupId, base.localAvatar.doId)
        self.currentGroupJoined = groupId
        try:
            place = base.cr.playGame.getPlace()
        except:
            try:
                place = base.cr.playGame.hood.loader.place
            except:
                place = base.cr.playGame.hood.place
        place.requestTeleport(groupId, groupId, base.localAvatar.defaultShard, -1)

    def leaveGroup(self, groupId, buttonTuple):
        self.acceptOnce('confLeave', self.confirmLeaveGroup, extraArgs=[groupId, buttonTuple])
        self.joinDialog = TTDialog.TTGlobalDialog(message='Are you sure you want to leave this group?', doneEvent='confLeave', style=4)

    def confirmLeaveGroup(self, groupId, buttonTuple):
        doneStatus = self.joinDialog.doneStatus
        self.joinDialog.cleanup()
        del self.joinDialog
        if doneStatus is not 'ok':
            return
        if not base.cr.groupManager.isInGroup(base.localAvatar.doId, groupId):
            return
        base.cr.groupManager.d_removePlayerFromGroup(groupId, base.localAvatar.doId)
        self.currentGroupJoined = None
        try:
            place = base.cr.playGame.getPlace()
        except:
            try:
                place = base.cr.playGame.hood.loader.place
            except:
                place = base.cr.playGame.hood.place
        hoodId = -1
        gids = {10000:1000, 11000:5000, 12000:9000, 13000:3000}
        hoodId = gids.get(groupId)
        if hoodId is None:
            return
        place.requestTeleport(hoodId, hoodId, base.localAvatar.defaultShard, -1)

    def getPopColor(self, pop):
        if pop <= self.lowPop:
            newColor = POP_COLORS[0]
        elif pop <= self.midPop:
            newColor = POP_COLORS[1]
        else:
            newColor = POP_COLORS[2]
        return newColor

    def getPopText(self, pop):
        if pop <= self.lowPop:
            popText = TTLocalizer.ShardPageLow
        elif pop <= self.midPop:
            popText = TTLocalizer.ShardPageMed
        else:
            popText = TTLocalizer.ShardPageHigh
        return popText

    def getPopChoiceHandler(self, pop):
        if pop <= self.midPop:
            if self.noTeleport and not self.showPop:
                handler = self.shardChoiceReject
            else:
                handler = self.choseShard
        elif self.showPop:
            handler = self.choseShard
        else:
            if localAvatar.adminAccess >= 200:
                handler = self.choseShard
            else:
                handler = self.shardChoiceReject
        return handler

    def getCurrentZoneId(self):
        try:
            zoneId = base.cr.playGame.getPlace().getZoneId()
        except:
            zoneId = None
        return zoneId

    def getCurrentShardId(self):
        zoneId = self.getCurrentZoneId()

        if zoneId != None and ZoneUtil.isWelcomeValley(zoneId):
            return ToontownGlobals.WelcomeValleyToken
        else:
            return base.localAvatar.defaultShard

    def createSuitHead(self, suitName):
        suitDNA = SuitDNA.SuitDNA()
        suitDNA.newSuit(suitName)
        suit = Suit.Suit()
        suit.setDNA(suitDNA)
        headParts = suit.getHeadParts()
        head = hidden.attachNewNode('head')
        for part in headParts:
            copyPart = part.copyTo(head)
            copyPart.setDepthTest(1)
            copyPart.setDepthWrite(1)
        self.fitGeometry(head, fFlip=1)
        suit.delete()
        suit = None
        return head

    def updateScrollList(self):
        curShardTuples = base.cr.listActiveShards()
        curShardTuples.sort(compareShardTuples)

        currentShardId = self.getCurrentShardId()
        actualShardId = base.localAvatar.defaultShard
        actualShardName = None
        anyChanges = 0
        totalPop = 0
        totalWVPop = 0
        currentMap = {}
        self.shardButtons = []

        for i in xrange(len(curShardTuples)):

            shardId, name, pop, WVPop, invasionStatus = curShardTuples[i]

            if shardId == actualShardId:
                actualShardName = name

            totalPop += pop
            totalWVPop += WVPop
            currentMap[shardId] = 1
            buttonTuple = self.shardButtonMap.get(shardId)

            if buttonTuple == None:
                buttonTuple = self.makeShardButton(shardId, name, pop)
                self.shardButtonMap[shardId] = buttonTuple
                anyChanges = 1
            else:
                buttonTuple[1]['image_color'] = self.getPopColor(pop)
                buttonTuple[1]['text'] = str(pop)
                buttonTuple[1]['command'] = self.reloadRightBrain
                buttonTuple[1]['extraArgs'] = [pop, name, shardId, buttonTuple]
                buttonTuple[2]['command'] = self.reloadRightBrain
                buttonTuple[2]['extraArgs'] = [pop, name, shardId, buttonTuple]

            self.shardButtons.append(buttonTuple[0])

            if invasionStatus:
                setupInvasionMarker(buttonTuple[3], invasionStatus)
            else:
                removeInvasionMarker(buttonTuple[3])

        for shardId, buttonTuple in self.shardButtonMap.items():

            if shardId not in currentMap:
                buttonTuple[3].removeNode()
                buttonTuple[0].destroy()
                del self.shardButtonMap[shardId]
                anyChanges = 1

        if anyChanges:
            self.regenerateScrollList()

        self.totalPopulationText['text'] = TTLocalizer.ShardPagePopulationTotal % totalPop
        helpText = TTLocalizer.ShardPageHelpIntro

        if actualShardName:
            helpText += TTLocalizer.ShardPageHelpWhere % actualShardName

        if not self.book.safeMode:
            helpText += TTLocalizer.ShardPageHelpMove

    def enter(self):
        self.askForShardInfoUpdate()
        self.updateScrollList()
        currentShardId = self.getCurrentShardId()
        buttonTuple = self.shardButtonMap.get(currentShardId)
        if buttonTuple:
            i = self.shardButtons.index(buttonTuple[0])
            self.scrollList.scrollTo(i, centered=1)
            self.firstLoadShard(buttonTuple)
        ShtikerPage.ShtikerPage.enter(self)
        self.accept('shardInfoUpdated', self.updateScrollList)

    def exit(self):
        for shardId, buttonTuple in self.shardButtonMap.items():
            buttonTuple[1]['state'] = DGG.NORMAL
            buttonTuple[2]['state'] = DGG.NORMAL
        self.ignore('shardInfoUpdated')
        self.ignore('ShardPageConfirmDone')
        taskMgr.remove('ShardPageUpdateTask-doLater')
        ShtikerPage.ShtikerPage.exit(self)

    def shardChoiceReject(self, shardId):
        self.confirm = TTDialog.TTGlobalDialog(doneEvent='ShardPageConfirmDone', message=TTLocalizer.ShardPageChoiceReject, style=TTDialog.Acknowledge)
        self.confirm.show()
        self.accept('ShardPageConfirmDone', self.__handleConfirm)

    def __handleConfirm(self):
        self.ignore('ShardPageConfirmDone')
        self.confirm.cleanup()
        del self.confirm

    def choseShard(self, shardId):
        zoneId = self.getCurrentZoneId()
        canonicalHoodId = ZoneUtil.getCanonicalHoodId(base.localAvatar.lastHood)
        currentShardId = self.getCurrentShardId()

        if self.currentGroupJoined:
            self.rejectGroup(5)
            return
        if shardId == currentShardId:
            return
        elif shardId == base.localAvatar.defaultShard:
            self.doneStatus = {'mode': 'teleport', 'hood': canonicalHoodId}
            messenger.send(self.doneEvent)
        else:
            try:
                place = base.cr.playGame.getPlace()
            except:
                try:
                    place = base.cr.playGame.hood.loader.place
                except:
                    place = base.cr.playGame.hood.place
            place.requestTeleport(canonicalHoodId, canonicalHoodId, shardId, -1)
