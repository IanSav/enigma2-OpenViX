from time import localtime, time, strftime, mktime

from enigma import eServiceReference, eTimer, eServiceCenter, ePoint

from Screens.HelpMenu import HelpableScreen
from Components.About import about
from Components.ActionMap import HelpableActionMap, HelpableNumberActionMap
from Components.Button import Button
from Components.config import config, configfile, ConfigClock
from Components.EpgListGraph import EPGListGraph, TimelineText, EPG_TYPE_INFOBARGRAPH, EPG_TYPE_GRAPH, MAX_TIMELINES
from EpgSelectionBase import EPGSelectionBase, EPGBouquetSelection
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Sources.ServiceEvent import ServiceEvent
from Components.Sources.Event import Event
from Components.UsageConfig import preferredTimerPath
from Screens.TimerEdit import TimerSanityConflict
from Screens.EventView import EventViewEPGSelect, EventViewSimple
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.PictureInPicture import PictureInPicture
from Screens.Setup import Setup
from Screens.TimeDateInput import TimeDateInput
from ServiceReference import ServiceReference

# Various value are in minutes, while others are in seconds.
# Use this to remind us what is going on...
SECS_IN_MIN = 60

class EPGSelectionGraph(EPGSelectionBase, EPGBouquetSelection):
	EMPTY = 0
	ADD_TIMER = 1
	REMOVE_TIMER = 2
	ZAP = 1

	def __init__(self, session, EPGtype = 'graph', zapFunc = None, bouquetChangeCB=None, serviceChangeCB = None, startBouquet = None, startRef = None, bouquets = None):
		print "[EPGSelectionGraph]"
		if EPGtype == 'graph':
			type = EPG_TYPE_GRAPH
		else:
			type = EPG_TYPE_INFOBARGRAPH
		EPGSelectionBase.__init__(self, type, session, zapFunc, bouquetChangeCB, serviceChangeCB, startBouquet, startRef, bouquets)

		now = time() - int(config.epg.histminutes.value) * SECS_IN_MIN
		if self.type == EPG_TYPE_GRAPH:
			graphic = config.epgselection.graph_type_mode.value == "graphics"
			self.ask_time = self.ask_time = now - now % (int(config.epgselection.graph_roundto.value) * SECS_IN_MIN)
			if not config.epgselection.graph_pig.value:
				self.skinName = 'GraphicalEPG'
			else:
				self.skinName = 'GraphicalEPGPIG'
		else:
			graphic = config.epgselection.infobar_type_mode.value == "graphics"
			self.ask_time = self.ask_time = now - now % (int(config.epgselection.infobar_roundto.value) * SECS_IN_MIN)
			self.skinName = 'GraphicalInfoBarEPG'
		self.closeRecursive = False
		EPGBouquetSelection.__init__(self, graphic)

		self['timeline_text'] = TimelineText(self.type, graphic)
		self['Event'] = Event()
		self['primetime'] = Label(_('PRIMETIME'))
		self['change_bouquet'] = Label(_('CHANGE BOUQUET'))
		self['jump'] = Label(_('JUMP 24 HOURS'))
		self['page'] = Label(_('PAGE UP/DOWN'))
		self.time_lines = []
		for x in range(0, MAX_TIMELINES):
			pm = Pixmap()
			self.time_lines.append(pm)
			self['timeline%d' % x] = pm

		self['timeline_now'] = Pixmap()
		self.updateTimelineTimer = eTimer()
		self.updateTimelineTimer.callback.append(self.moveTimeLines)
		self.updateTimelineTimer.start(60000)

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
				'nextService': (self.nextService, _('Jump forward 24 hours')),
				'prevService': (self.prevService, _('Jump back 24 hours')),
				'nextBouquet': (self.nextBouquet, _('Go to next bouquet')),
				'prevBouquet': (self.prevBouquet, _('Go to previous bouquet')),
				'input_date_time': (self.enterDateTime, _('Go to specific data/time')),
				'epg': (self.epgButtonPressed, _('Show single epg for current channel')),
				'info': (self.Info, _('Show detailed event info')),
				'infolong': (self.InfoLong, _('Show single epg for current channel')),
				'tv': (self.Bouquetlist, _('Toggle between bouquet/epg lists')),
				'tvlong': (self.togglePIG, _('Toggle picture In graphics')),
				'menu': (self.createSetup, _('Setup menu'))
			}, -1)
		self['epgactions'].csel = self

		self['input_actions'] = HelpableNumberActionMap(self, 'NumberActions',
			{
				'1': (self.keyNumberGlobal, _('Reduce time scale')),
				'2': (self.keyNumberGlobal, _('Page up')),
				'3': (self.keyNumberGlobal, _('Increase time scale')),
				'4': (self.keyNumberGlobal, _('page left')),
				'5': (self.keyNumberGlobal, _('Jump to current time')),
				'6': (self.keyNumberGlobal, _('Page right')),
				'7': (self.keyNumberGlobal, _('No of items switch (increase or reduced)')),
				'8': (self.keyNumberGlobal, _('Page down')),
				'9': (self.keyNumberGlobal, _('Jump to prime time')),
				'0': (self.keyNumberGlobal, _('Move to home of list'))
			}, -1)
		self['input_actions'].csel = self

		self['list'] = EPGListGraph(type=self.type, selChangedCB=self.onSelectionChanged, timer=session.nav.RecordTimer, graphic=graphic)

	def createSetup(self):
		self.closeEventViewDialog()
		if self.type == EPG_TYPE_GRAPH:
			key = 'epggraphical'
		else:
			key = 'epginfobargraphical'
		self.session.openWithCallback(self.onSetupClose, Setup, key)

	def onSetupClose(self, test = None):
		if self.type == EPG_TYPE_GRAPH:
			self.close('reopengraph')
		else:
			self.close('reopeninfobargraph')

	def onCreate(self):
		print "[EPGSelectionGraph] onCreate"
		self['list'].recalcEntrySize()
		self.getCurrentCursorLocation = None
		self.BouquetRoot = self.startBouquet.toString().startswith('1:7:0')
		# set time_base on grid widget so that timeline shows correct time
		self['list'].time_base = self.ask_time
		self['timeline_text'].setEntries(self['list'], self['timeline_now'], self.time_lines, False)
		self['lab1'].show()
		self.show()
		self.listTimer.start(1, True)

	def loadEPGData(self):
		print "[EPGSelectionGraph] loadEPGData"
		serviceref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		self._populateBouquetList()
		self['list'].fillEPGNoRefresh(self.services, self.ask_time)
		if self.type == EPG_TYPE_INFOBARGRAPH or not config.epgselection.graph_channel1.value:
			self['list'].moveToService(serviceref)
		self['list'].setCurrentlyPlaying(serviceref)
		self.moveTimeLines()
		self['lab1'].hide()

	def refreshlist(self):
		self.refreshTimer.stop()
		if self.getCurrentCursorLocation:
			self.ask_time = self.getCurrentCursorLocation
			self.getCurrentCursorLocation = None
		self['list'].fillEPG(None, self.ask_time)
		self.moveTimeLines()

	def togglePIG(self):
		if not config.epgselection.graph_pig.value:
			config.epgselection.graph_pig.setValue(True)
		else:
			config.epgselection.graph_pig.setValue(False)
		config.epgselection.graph_pig.save()
		configfile.save()
		self.close('reopengraph')

	def updEvent(self, dir, visible = True):
		ret = self['list'].selEntry(dir, visible)
		if ret:
			self.moveTimeLines(True)

	def moveTimeLines(self, force = False):
		self.updateTimelineTimer.start((60 - int(time()) % 60) * 1000)
		self['timeline_text'].setEntries(self['list'], self['timeline_now'], self.time_lines, force)
		self['list'].l.invalidate()

	def leftPressed(self):
		self.updEvent(-1)

	def rightPressed(self):
		self.updEvent(+1)

	def BouquetOK(self):
		self.BouquetRoot = False
		now = time() - int(config.epg.histminutes.value) * SECS_IN_MIN
		self.services = self.getBouquetServices(self.getCurrentBouquet())
		if self.type == EPG_TYPE_GRAPH:
			self.ask_time = now - now % (int(config.epgselection.graph_roundto.value) * SECS_IN_MIN)
		elif self.type == EPG_TYPE_INFOBARGRAPH:
			self.ask_time = now - now % (int(config.epgselection.infobar_roundto.value) * SECS_IN_MIN)
		self['list'].setTimeFocus(time())
		self['list'].fillEPG(self.services, self.ask_time)
		self.moveTimeLines(True)
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
		self.updEvent(+24)

	def prevService(self):
		self.updEvent(-24)

	def enterDateTime(self):
		use_time = None
		if self.type == EPG_TYPE_GRAPH:
			use_time = config.epgselection.graph_prevtime
		elif self.type == EPG_TYPE_INFOBARGRAPH:
			use_time = config.epgselection.infobar_prevtime
		if use_time:
			self.session.openWithCallback(self.onDateTimeInputClosed, TimeDateInput, use_time)

	def onDateTimeInputClosed(self, ret):
		if len(ret) > 1:
			if ret[0]:
				self.ask_time = ret[1]
				now = time() - int(config.epg.histminutes.value) * SECS_IN_MIN
				if self.type == EPG_TYPE_GRAPH:
					self.ask_time -= self.ask_time % (int(config.epgselection.graph_roundto.value) * SECS_IN_MIN)
				elif self.type == EPG_TYPE_INFOBARGRAPH:
					self.ask_time -= self.ask_time % (int(config.epgselection.infobar_roundto.value) * SECS_IN_MIN)
				l = self['list']
				# place the entered time halfway across the grid
				l.setTimeFocus(self.ask_time)
				l.fillEPG(None, self.ask_time - l.getTimeEpoch() * SECS_IN_MIN / 2)
				self.moveTimeLines(True)
		if self.eventviewDialog and self.type == EPG_TYPE_INFOBARGRAPH:
			self.infoKeyPressed(True)

	def infoKeyPressed(self, eventviewopen=False):
		cur = self['list'].getCurrent()
		event = cur[0]
		service = cur[1]
		if event is not None and not self.eventviewDialog and not eventviewopen:
			if self.type == EPG_TYPE_INFOBARGRAPH:
				self.eventviewDialog = self.session.instantiateDialog(EventViewSimple,event, service, skin='InfoBarEventView')
				self.eventviewDialog.show()
			else:
				self.session.open(EventViewEPGSelect, event, service, callback=self.eventViewCallback, similarEPGCB=self.openSimilarList)
		elif self.eventviewDialog and not eventviewopen:
			self.eventviewDialog.hide()
			del self.eventviewDialog
			self.eventviewDialog = None
		elif event is not None and self.eventviewDialog and eventviewopen:
			if self.type == EPG_TYPE_INFOBARGRAPH:
				self.eventviewDialog.hide()
				self.eventviewDialog = self.session.instantiateDialog(EventViewSimple,event, service, skin='InfoBarEventView')
				self.eventviewDialog.show()

	def eventViewCallback(self, setEvent, setService, val):
		l = self['list']
		old = l.getCurrent()
		self.updEvent(val, False)
		cur = l.getCurrent()
		if cur[0] is None and cur[1].ref != old[1].ref:
			self.eventViewCallback(setEvent, setService, val)
		else:
			setService(cur[1])
			setEvent(cur[0])

	def keyNumberGlobal(self, number):
		# Set up some values for the differences
		tp_var, rndto_var, pthr_var, ptmin_var = {
			EPG_TYPE_GRAPH:        (config.epgselection.graph_prevtimeperiod, config.epgselection.graph_roundto,
						config.epgselection.graph_primetimehour, config.epgselection.graph_primetimemins),
			EPG_TYPE_INFOBARGRAPH: (config.epgselection.infobar_prevtimeperiod, config.epgselection.infobar_roundto,
						config.epgselection.infobar_primetimehour, config.epgselection.infobar_primetimemins),
			}[self.type]
		if number == 1:
			timeperiod = int(tp_var.value)
			if timeperiod > 60:
				timeperiod -= 30
				self['list'].setTimeEpoch(timeperiod)
				tp_var.setValue(str(timeperiod))
				self.moveTimeLines()
		elif number == 2:
			self.prevPage()
		elif number == 3:
			timeperiod = int(tp_var.value)
			if timeperiod < 300:
				timeperiod += 30
				self['list'].setTimeEpoch(timeperiod)
				tp_var.setValue(str(timeperiod))
				self.moveTimeLines()
		elif number == 4:
			self.updEvent(-2)
		elif number == 5:
			now = time() - int(config.epg.histminutes.value) * SECS_IN_MIN
			self.ask_time = now - now % (int(rndto_var.value) * SECS_IN_MIN)
			self['list'].setTimeFocus(time())
			self['list'].fillEPG(None, self.ask_time)
			self.moveTimeLines(True)
		elif number == 6:
			self.updEvent(+2)
		elif number == 7 and (self.type == EPG_TYPE_GRAPH):
			if config.epgselection.graph_heightswitch.value:
				config.epgselection.graph_heightswitch.setValue(False)
			else:
				config.epgselection.graph_heightswitch.setValue(True)
			self['list'].setItemsPerPage()
			self['list'].fillEPG(None)
			self.moveTimeLines()
		elif number == 8:
			self.nextPage()
		elif number == 9:
			basetime = localtime(self['list'].getTimeBase())
			basetime = (basetime[0], basetime[1], basetime[2], int(pthr_var.value), int(ptmin_var.value), 0, basetime[6], basetime[7], basetime[8])
			self.ask_time = mktime(basetime)
			if self.ask_time + 3600 < time():
				self.ask_time += 86400
			self['list'].fillEPG(None, self.ask_time)
			self.moveTimeLines(True)
		elif number == 0:
			self.toTop()
			now = time() - int(config.epg.histminutes.value) * SECS_IN_MIN
			self.ask_time = now - now % (int(rndto_var.value) * SECS_IN_MIN)
			self['list'].setTimeFocus(time())
			self['list'].fillEPG(None, self.ask_time)
			self.moveTimeLines()
