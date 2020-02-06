from time import localtime, time, strftime, mktime

from enigma import eServiceReference, eTimer, eServiceCenter, ePoint

from Screens.HelpMenu import HelpableScreen
from Components.About import about
from Components.ActionMap import HelpableActionMap, HelpableNumberActionMap
from Components.Button import Button
from Components.config import config, configfile, ConfigClock
from Components.EpgListOther import EPGListOther
from Components.EpgListBase import EPG_TYPE_ENHANCED
from EpgSelectionBase import EPGSelectionBase, EPGNumberZap
from Screens.EventView import EventViewEPGSelect
from Screens.Setup import Setup
from ServiceReference import ServiceReference

class EPGSelectionEnhanced(EPGSelectionBase, EPGNumberZap):
	def __init__(self, session, servicelist = None, zapFunc = None, bouquetChangeCB=None, serviceChangeCB = None, startBouquet = None, startRef = None, bouquets = None):
		print "[EPGSelectionEnhanced]"
		EPGSelectionBase.__init__(self, EPG_TYPE_ENHANCED, session, zapFunc, bouquetChangeCB, serviceChangeCB, startBouquet, startRef, bouquets)
		EPGNumberZap.__init__(self)

		self.skinName = 'EPGSelection'

		self['epgactions'] = HelpableActionMap(self, 'EPGSelectActions',
			{
				'nextBouquet': (self.nextBouquet, _('Go to next bouquet')),
				'prevBouquet': (self.prevBouquet, _('Go to previous bouquet')),
				'nextService': (self.nextService, _('Go to next channel')),
				'prevService': (self.prevService, _('Go to previous channel')),
				'info': (self.Info, _('Show detailed event info')),
				'infolong': (self.InfoLong, _('Show single epg for current channel')),
				'menu': (self.createSetup, _('Setup menu'))
			}, -1)
		self['epgactions'].csel = self
		self['epgcursoractions'] = HelpableActionMap(self, 'DirectionActions',
			{
				'left': (self.prevPage, _('Move up a page')),
				'right': (self.nextPage, _('Move down a page')),
				'up': (self.moveUp, _('Go to previous channel')),
				'down': (self.moveDown, _('Go to next channel'))
			}, -1)
		self['epgcursoractions'].csel = self
			
		self.list = []
		self.servicelist = servicelist
		self.currentService = self.session.nav.getCurrentlyPlayingServiceOrGroup()

		self['list'] = EPGListOther(type=self.type, selChangedCB=self.onSelectionChanged, timer=session.nav.RecordTimer)

	def createSetup(self):
		self.closeEventViewDialog()
		self.session.openWithCallback(self.onSetupClose, Setup, 'epgenhanced')

	def onSetupClose(self, test = None):
		self['list'].sortSingleEPG(int(config.epgselection.sort.value))
		self['list'].setFontsize()
		self['list'].setItemsPerPage()
		self['list'].recalcEntrySize()

	def onCreate(self):
		self['list'].recalcEntrySize()
		service = ServiceReference(self.servicelist.getCurrentSelection())
		self['Service'].newService(service.ref)
		title = ServiceReference(self.servicelist.getRoot()).getServiceName() + ' - ' + service.getServiceName()
		self.setTitle(title)
		self['list'].fillSingleEPG(service)
		self['list'].sortSingleEPG(int(config.epgselection.sort.value))
		self.show()

	def loadEPGData(self):
		pass
		
	def refreshlist(self):
		self.refreshTimer.stop()
		try:
			service = ServiceReference(self.servicelist.getCurrentSelection())
			if not self.cureventindex:
				index = self['list'].getCurrentIndex()
			else:
				index = self.cureventindex
				self.cureventindex = None
			self['list'].fillSingleEPG(service)
			self['list'].sortSingleEPG(int(config.epgselection.sort.value))
			self['list'].setCurrentIndex(index)
		except:
			pass

	def nextBouquet(self):
		self.CurrBouquet = self.servicelist.getCurrentSelection()
		self.CurrService = self.servicelist.getRoot()
		self.servicelist.nextBouquet()
		self.onCreate()

	def prevBouquet(self):
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
		self['list'].sortSingleEPG(int(config.epgselection.sort.value))
