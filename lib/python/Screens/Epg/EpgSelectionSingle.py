from Components.ActionMap import HelpableActionMap
from Components.config import config, configfile
from Components.EpgListOther import EPGListOther
from Components.EpgListBase import EPG_TYPE_SINGLE
from EpgSelectionBase import EPGSelectionBase
from Screens.EventView import EventViewEPGSelect
from Screens.Setup import Setup
from ServiceReference import ServiceReference

class EPGSelectionSingle(EPGSelectionBase):
	def __init__(self, session, service):
		print "[EPGSelectionSingle]"
		EPGSelectionBase.__init__(self, EPG_TYPE_SINGLE, session)

		self.skinName = 'EPGSelection'
		self.currentService = ServiceReference(service)
		self['epgactions'] = HelpableActionMap(self, 'EPGSelectActions',
			{
				'info': (self.Info, _('Show detailed event info')),
				'epg': (self.Info, _('Show detailed event info')),
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

		self['list'] = EPGListOther(type=self.type, selChangedCB=self.onSelectionChanged, timer=session.nav.RecordTimer)

	def createSetup(self):
		self.closeEventViewDialog()
		self.session.openWithCallback(self.onSetupClose, Setup, 'epgsingle')

	def onSetupClose(self, test = None):
		self['list'].sortSingleEPG(int(config.epgselection.sort.value))
		self['list'].setFontsize()
		self['list'].setItemsPerPage()
		self['list'].recalcEntrySize()

	def onCreate(self):
		self['list'].recalcEntrySize()
		service = self.currentService
		self['Service'].newService(service.ref)
		title = service.getServiceName()
		self.setTitle(title)
		self['list'].fillSingleEPG(service)
		self['list'].sortSingleEPG(int(config.epgselection.sort.value))
		self['lab1'].show()
		self.show()

	def loadEPGData(self):
		pass

	def refreshlist(self):
		self.refreshTimer.stop()
		try:
			service = self.currentService
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

	def closeScreen(self):
		self.close()
