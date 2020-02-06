from time import time

from Components.ActionMap import HelpableActionMap
from Components.config import config, ConfigClock
from Components.EpgListMulti import EPGListMulti
from Components.EpgListBase import EPG_TYPE_MULTI
from EpgSelectionBase import EPGSelectionBase, EPGBouquetSelection
from Components.Label import Label
from Components.Pixmap import Pixmap
from Screens.EventView import EventViewEPGSelect
from Screens.TimeDateInput import TimeDateInput

# Various value are in minutes, while others are in seconds.
# Use this to remind us what is going on...
SECS_IN_MIN = 60

class EPGSelectionMulti(EPGSelectionBase, EPGBouquetSelection):
	def __init__(self, session, zapFunc, startBouquet, startRef, bouquets):
		print "[EPGSelectionMulti]"
		EPGSelectionBase.__init__(self, EPG_TYPE_MULTI, session, zapFunc, None, None, startBouquet, startRef, bouquets)
		EPGBouquetSelection.__init__(self, False)

		self.skinName = 'EPGSelectionMulti'
		self['now_button'] = Pixmap()
		self['next_button'] = Pixmap()
		self['more_button'] = Pixmap()
		self['now_button_sel'] = Pixmap()
		self['next_button_sel'] = Pixmap()
		self['more_button_sel'] = Pixmap()
		self['now_text'] = Label()
		self['next_text'] = Label()
		self['more_text'] = Label()
		self['date'] = Label()

		self['epgcursoractions'] = HelpableActionMap(self, 'DirectionActions',
			{
				'left': (self.leftPressed, _('Go to previous event')),
				'right': (self.rightPressed, _('Go to next event')),
				'up': (self.moveUp, _('Go to previous channel')),
				'down': (self.moveDown, _('Go to next channel'))
			}, -1)
		self['epgcursoractions'].csel = self

		self['epgactions'] = HelpableActionMap(self, 'EPGSelectActions',
			{
				'nextService': (self.nextPage, _('Move down a page')),
				'prevService': (self.prevPage, _('Move up a page')),
				'nextBouquet': (self.nextBouquet, _('Go to next bouquet')),
				'prevBouquet': (self.prevBouquet, _('Go to previous bouquet')),
				'input_date_time': (self.enterDateTime, _('Go to specific data/time')),
				'epg': (self.epgButtonPressed, _('Show single epg for current channel')),
				'info': (self.Info, _('Show detailed event info')),
				'infolong': (self.InfoLong, _('Show single epg for current channel')),
				'tv': (self.Bouquetlist, _('Toggle between bouquet/epg lists')),
				'menu': (self.createSetup, _('Setup menu'))
			}, -1)
		self['epgactions'].csel = self

		self['list'] = EPGListMulti(selChangedCB=self.onSelectionChanged, timer=session.nav.RecordTimer)

	def createSetup(self):
		self.closeEventViewDialog()
		self.session.openWithCallback(self.onSetupClose, Setup, 'epgmulti')

	def onSetupClose(self, test = None):
		self['list'].setFontsize()
		self['list'].setItemsPerPage()
		self['list'].recalcEntrySize()

	def onCreate(self):
		self['list'].recalcEntrySize()
		self['lab1'].show()
		self.show()
		self.listTimer.start(1, True)

	def loadEPGData(self):
		self._populateBouquetList()
		serviceref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		self['list'].fillMultiEPG(self.services, self.ask_time)
		self['list'].moveToService(serviceref)
		self['list'].setCurrentlyPlaying(serviceref)
		self['lab1'].hide()

	def refreshlist(self):
		self.refreshTimer.stop()
		self['list'].fillMultiEPG(self.services, self.ask_time)

	def leftPressed(self):
		self['list'].updateMultiEPG(-1)

	def rightPressed(self):
		self['list'].updateMultiEPG(1)

	def BouquetOK(self):
		self.BouquetRoot = False
		now = time() - int(config.epg.histminutes.value) * SECS_IN_MIN
		self.services = self.getBouquetServices(self.getCurrentBouquet())
		self['list'].fillMultiEPG(self.services, self.ask_time)
		self['list'].instance.moveSelectionTo(0)
		self.setTitle(self['bouquetlist'].getCurrentBouquet())
		self.BouquetlistHide(False)

	def nextBouquet(self):
		self.moveBouquetDown()
		self.BouquetOK()

	def prevBouquet(self):
		self.moveBouquetUp()
		self.BouquetOK()

	def nextService(self):
		if self.serviceChangeCB:
			self.serviceChangeCB(1, self)

	def prevService(self):
		if self.serviceChangeCB:
			self.serviceChangeCB(-1, self)

	def enterDateTime(self):
		global mepg_config_initialized
		use_time = None
		if not mepg_config_initialized:
			config.misc.prev_mepg_time = ConfigClock(default=time())
			mepg_config_initialized = True
		use_time = config.misc.prev_mepg_time
		if use_time:
			self.session.openWithCallback(self.onDateTimeInputClosed, TimeDateInput, use_time)

	def onDateTimeInputClosed(self, ret):
		if len(ret) > 1:
			if ret[0]:
				self.ask_time = ret[1]
				self['list'].fillMultiEPG(self.services, self.ask_time)

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
		if cur[0] is None and cur[1].ref != old[1].ref:
			self.eventViewCallback(setEvent, setService, val)
		else:
			setService(cur[1])
			setEvent(cur[0])
