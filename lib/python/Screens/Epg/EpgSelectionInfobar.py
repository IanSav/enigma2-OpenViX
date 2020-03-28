from enigma import eServiceReference

from Components.ActionMap import HelpableActionMap
from Components.config import config, configfile
from Components.Epg.EpgListSingle import EPGListSingle
from Components.Epg.EpgListBase import EPG_TYPE_INFOBAR
from EpgSelectionBase import EPGSelectionBase
from Components.Sources.Event import Event
from Screens.EventView import EventViewEPGSelect, EventViewSimple
from Screens.Setup import Setup
from ServiceReference import ServiceReference

class EPGSelectionInfobar(EPGSelectionBase):
	def __init__(self, session, servicelist = None, zapFunc = None, bouquetChangeCB=None, serviceChangeCB = None, startBouquet = None, startRef = None, bouquets = None):
		print "[EPGSelectionInfobar] ------- NEW VERSION -------"
		EPGSelectionBase.__init__(self, EPG_TYPE_INFOBAR, session, zapFunc, bouquetChangeCB, serviceChangeCB, startBouquet, startRef, bouquets)

		self.skinName = 'QuickEPG'
		self['epgactions'] = HelpableActionMap(self, 'EPGSelectActions',
			{
				'nextBouquet': (self.nextBouquet, _('Go to next bouquet')),
				'prevBouquet': (self.prevBouquet, _('Go to previous bouquet')),
				'nextService': (self.nextPage, _('Move down a page')),
				'prevService': (self.prevPage, _('Move up a page')),
				'epg': (self.epgButtonPressed, _('Show single epg for current channel')),
				'info': (self.Info, _('Show detailed event info')),
				'infolong': (self.InfoLong, _('Show single epg for current channel')),
				'menu': (self.createSetup, _('Setup menu'))
			}, -1)
		self['epgactions'].csel = self
		self['epgcursoractions'] = HelpableActionMap(self, 'DirectionActions',
			{
				'left': (self.prevService, _('Go to previous channel')),
				'right': (self.nextService, _('Go to next channel')),
				'up': (self.moveUp, _('Go to previous channel')),
				'down': (self.moveDown, _('Go to next channel'))
			}, -1)
		self['epgcursoractions'].csel = self
		self.list = []
		self.servicelist = servicelist
		self.currentService = self.session.nav.getCurrentlyPlayingServiceOrGroup()

		self['list'] = EPGListSingle(selChangedCB=self.onSelectionChanged, timer=session.nav.RecordTimer,
			itemsPerPageConfig = config.epgselection.infobar_itemsperpage,
			eventfsConfig = config.epgselection.infobar_eventfs)

	def createSetup(self):
		self.closeEventViewDialog()
		self.session.openWithCallback(self.onSetupClose, Setup, 'epginfobar')

	def onSetupClose(self, test = None):
		self.close('reopeninfobar')

	def onCreate(self):
		self['list'].recalcEntrySize()
		service = ServiceReference(self.servicelist.getCurrentSelection())
		title = ServiceReference(self.servicelist.getRoot()).getServiceName()
		self['Service'].newService(service.ref)
		if title:
			title = title + ' - ' + service.getServiceName()
		else:
			title = service.getServiceName()
		self.setTitle(title)
		self['list'].fillEPG(service)
		self['list'].sortEPG(int(config.epgselection.sort.value))
		self['lab1'].show()
		self.show()

	def refreshList(self):
		self.refreshTimer.stop()
		try:
			service = ServiceReference(self.servicelist.getCurrentSelection())
			if not self.cureventindex:
				index = self['list'].getCurrentIndex()
			else:
				index = self.cureventindex
				self.cureventindex = None
			self['list'].fillEPG(service)
			self['list'].sortEPG(int(config.epgselection.sort.value))
			self['list'].setCurrentIndex(index)
		except:
			pass

	def bouquetChanged(self):
		self.BouquetRoot = False
		now = time() - int(config.epg.histminutes.value) * SECS_IN_MIN
		self.services = self.getBouquetServices(self.getCurrentBouquet())
		self['list'].instance.moveSelectionTo(0)
		self.setTitle(self['bouquetlist'].getCurrentBouquet())
		self.bouquetListHide()

	def nextBouquet(self):
		if config.usage.multibouquet.value:
			self.CurrBouquet = self.servicelist.getCurrentSelection()
			self.CurrService = self.servicelist.getRoot()
			self.servicelist.nextBouquet()
			self.onCreate()

	def prevBouquet(self):
		if config.usage.multibouquet.value:
			self.CurrBouquet = self.servicelist.getCurrentSelection()
			self.CurrService = self.servicelist.getRoot()
			self.servicelist.prevBouquet()
			self.onCreate()

	def nextService(self):
		self.CurrBouquet = self.servicelist.getCurrentSelection()
		self.CurrService = self.servicelist.getRoot()
		self['list'].instance.moveSelectionTo(0)
		if self.servicelist.inBouquet():
			prev = self.servicelist.getCurrentSelection()
			if prev:
				prev = prev.toString()
				while True:
					if config.usage.quickzap_bouquet_change.value and self.servicelist.atEnd():
						self.servicelist.nextBouquet()
					else:
						self.servicelist.moveDown()
					cur = self.servicelist.getCurrentSelection()
					if not cur or (not (cur.flags & 64)) or cur.toString() == prev:
						break
		else:
			self.servicelist.moveDown()
		if self.isPlayable():
			self.onCreate()
			if not self['list'].getCurrent()[1] and config.epgselection.overjump.value:
				self.nextService()
		else:
			self.nextService()

	def isPlayable(self):
		current = ServiceReference(self.servicelist.getCurrentSelection())
		return not current.ref.flags & (eServiceReference.isMarker | eServiceReference.isDirectory)

	def prevService(self):
		self.CurrBouquet = self.servicelist.getCurrentSelection()
		self.CurrService = self.servicelist.getRoot()
		self['list'].instance.moveSelectionTo(0)
		if self.servicelist.inBouquet():
			prev = self.servicelist.getCurrentSelection()
			if prev:
				prev = prev.toString()
				while True:
					if config.usage.quickzap_bouquet_change.value:
						if self.servicelist.atBegin():
							self.servicelist.prevBouquet()
					self.servicelist.moveUp()
					cur = self.servicelist.getCurrentSelection()
					if not cur or (not (cur.flags & 64)) or cur.toString() == prev:
						break
		else:
			self.servicelist.moveUp()
		if self.isPlayable():
			self.onCreate()
			if not self['list'].getCurrent()[1] and config.epgselection.overjump.value:
				self.prevService()
		else:
			self.prevService()

	def infoKeyPressed(self, eventviewopen=False):
		cur = self['list'].getCurrent()
		event = cur[0]
		service = cur[1]
		if event is not None and not self.eventviewDialog and not eventviewopen:
			self.session.open(EventViewEPGSelect, event, service, callback=self.eventViewCallback, similarEPGCB=self.openSimilarList)
		elif self.eventviewDialog and not eventviewopen:
			self.eventviewDialog.hide()
			del self.eventviewDialog
			self.eventviewDialog = None
		elif event is not None and self.eventviewDialog and eventviewopen:
			self.eventviewDialog.hide()
			self.eventviewDialog = self.session.instantiateDialog(EventViewSimple,event, service, skin='InfoBarEventView')
			self.eventviewDialog.show()

	def eventViewCallback(self, setEvent, setService, val):
		l = self['list']
		old = l.getCurrent()
		if val == -1:
			self.moveUp()
		elif val == +1:
			self.moveDown()
		cur = l.getCurrent()
		setService(cur[1])
		setEvent(cur[0])

	def sortEpg(self):
		if config.epgselection.sort.value == '0':
			config.epgselection.sort.setValue('1')
		else:
			config.epgselection.sort.setValue('0')
		config.epgselection.sort.save()
		configfile.save()
		self['list'].sortEPG(int(config.epgselection.sort.value))
