import Entity

class VisibilityExtender(Entity.Entity):

    def __init__(self, level, entId):
        Entity.Entity.__init__(self, level, entId)
        self.initVisExt()

    def initVisExt(self):
        self.extended = 0
        self.zoneEntId = self.getZoneEntId()
        self.eventName = None
        if self.event is not None:
            self.eventName = self.getOutputEventName(self.event)
            self.accept(self.eventName, self.handleEvent)

    def destroyVisExt(self):
        if self.eventName is not None:
            self.ignore(self.eventName)
        if self.extended:
            self.retract()

    def handleEvent(self, doExtend):
        if doExtend:
            if not self.extended:
                self.extend()
        elif self.extended:
            self.retract()

    def extend(self):
        zoneEnt = self.level.getEntity(self.getZoneEntId())
        zoneEnt.incrementRefCounts(self.newZones)
        self.extended = 1
        self.level.handleVisChange()

    def retract(self):
        zoneEnt = self.level.getEntity(self.getZoneEntId())
        zoneEnt.decrementRefCounts(self.newZones)
        self.extended = 0
        self.level.handleVisChange()

    def destroy(self):
        self.destroyVisExt()
        Entity.Entity.destroy(self)