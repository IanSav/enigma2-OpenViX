from Components.ActionMap import HelpableActionMap
from Components.config import config
from Components.Epg.EpgListSingle import EPGListSingle
from Components.Epg.EpgListBase import EPG_TYPE_SIMILAR
from EpgSelectionBase import EPGSelectionBase

class EPGSelectionSimilar(EPGSelectionBase):
	def __init__(self, session, service, eventid):
		print "[EPGSelectionSimilar]"
		EPGSelectionBase.__init__(self, EPG_TYPE_SIMILAR, session)

		self.currentService = service
		self.eventid = eventid
		self['epgactions'] = HelpableActionMap(self, 'EPGSelectActions',
			{
				'info': (self.Info, _('Show detailed event info')),
				'infolong': (self.InfoLong, _('Show single epg for current channel')),
				'menu': (self.createSetup, _('Setup menu'))
			}, -1)
		self['epgactions'].csel = self

		self['list'] = EPGListSingle(selChangedCB=self.onSelectionChanged, timer=session.nav.RecordTimer,
			itemsPerPageConfig = config.epgselection.enhanced_itemsperpage,
			eventfsConfig = config.epgselection.enhanced_eventfs)

	def onCreate(self):
		self['list'].recalcEntrySize()
		self['list'].fillSimilarList(self.currentService, self.eventid)
		self['lab1'].show()
		self.show()

	def refreshlist(self):
		self.refreshTimer.stop()

	def infoKeyPressed(self, eventviewopen=False):
		pass
