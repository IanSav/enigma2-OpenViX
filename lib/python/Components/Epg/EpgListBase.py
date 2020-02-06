import skin
from time import localtime, time, strftime

from enigma import eEPGCache, eListbox, eListboxPythonMultiContent, loadPNG, gFont, getDesktop, eRect, eSize, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER, RT_VALIGN_TOP, RT_WRAP, BT_SCALE, BT_KEEP_ASPECT_RATIO, BT_ALIGN_CENTER

from Components.GUIComponent import GUIComponent
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaBlend, MultiContentEntryPixmapAlphaTest
from Components.Renderer.Picon import getPiconName
from skin import parseColor, parseFont
from Tools.Alternatives import CompareWithAlternatives
from Components.config import config
from ServiceReference import ServiceReference
from Tools.Directories import resolveFilename, SCOPE_ACTIVE_SKIN
from Tools.TextBoundary import getTextBoundarySize

EPG_TYPE_SINGLE = 0
EPG_TYPE_MULTI = 1
EPG_TYPE_SIMILAR = 2
EPG_TYPE_ENHANCED = 3
EPG_TYPE_INFOBAR = 4
EPG_TYPE_GRAPH = 5
EPG_TYPE_INFOBARGRAPH = 7

class EPGListBase(GUIComponent):
	def __init__(self, type, selChangedCB = None, timer = None):
		print "[EPGListBase] Init"
		self.type = type
		self.time_base = None
		self.currentlyPlaying = None
		self.timer = timer
		self.onSelChanged = [ ]
		if selChangedCB is not None:
			self.onSelChanged.append(selChangedCB)
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()

		self.epgcache = eEPGCache.getInstance()

		# Common clock icons
		add = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_add.png'))
		pre = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_pre.png'))
		clock = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock.png'))
		zap = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_zap.png'))
		zaprec = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_zaprec.png'))
		prepost = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_prepost.png'))
		post = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_post.png'))
		self.clocks = [
			add, pre, clock, prepost, post,
			add, pre, zap, prepost, post,
			add, pre, zaprec, prepost, post,
			add, pre, clock, prepost, post]

		# Common selected clock icons
		pre = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_selpre.png'))
		prepost = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_selprepost.png'))
		post = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_selpost.png'))
		self.selclocks = [
			add, pre, clock, prepost, post,
			add, pre, zap, prepost, post,
			add, pre, zaprec, prepost, post]

		self.autotimericon = loadPNG(resolveFilename(SCOPE_ACTIVE_SKIN, 'icons/epgclock_autotimer.png'))

		self.nowEvPix = None
		self.nowSelEvPix = None
		self.othEvPix = None
		self.selEvPix = None
		self.othServPix = None
		self.nowServPix = None
		self.recEvPix = None
		self.recSelEvPix = None
		self.zapEvPix = None
		self.zapSelEvPix = None

		self.borderTopPix = None
		self.borderBottomPix = None
		self.borderLeftPix = None
		self.borderRightPix = None
		self.borderSelectedTopPix = None
		self.borderSelectedLeftPix = None
		self.borderSelectedBottomPix = None
		self.borderSelectedRightPix = None
		self.InfoPix = None
		self.selInfoPix = None
		self.graphicsloaded = False

		self.borderColor = 0xC0C0C0
		self.borderColorService = 0xC0C0C0

		self.foreColor = 0xffffff
		self.foreColorSelected = 0xffffff
		self.backColor = 0x2D455E
		self.backColorSelected = 0xd69600
		self.foreColorService = 0xffffff
		self.backColorService = 0x2D455E
		self.foreColorNow = 0xffffff
		self.foreColorNowSelected = 0xffffff
		self.backColorNow = 0x00825F
		self.backColorNowSelected = 0xd69600
		self.foreColorServiceNow = 0xffffff
		self.backColorServiceNow = 0x00825F

		self.foreColorRecord = 0xffffff
		self.backColorRecord = 0xd13333
		self.foreColorRecordSelected = 0xffffff
		self.backColorRecordSelected = 0x9e2626
		self.foreColorZap = 0xffffff
		self.backColorZap = 0x669466
		self.foreColorZapSelected = 0xffffff
		self.backColorZapSelected = 0x436143

		self.serviceFontNameGraph = "Regular"
		self.eventFontNameGraph = "Regular"
		self.eventFontNameSingle = "Regular"
		self.eventFontNameMulti = "Regular"
		self.serviceFontNameInfobar = "Regular"
		self.eventFontNameInfobar = "Regular"

		self.screenwidth = getDesktop(0).size().width()
		if self.screenwidth and self.screenwidth == 1920:
			self.serviceFontSizeGraph = 28
			self.eventFontSizeGraph = 28
			self.eventFontSizeSingle = 28
			self.eventFontSizeMulti = 28
			self.serviceFontSizeInfobar = 28
			self.eventFontSizeInfobar = 28
		else:
			self.serviceFontSizeGraph = 20
			self.eventFontSizeGraph = 20
			self.eventFontSizeSingle = 20
			self.eventFontSizeMulti = 20
			self.serviceFontSizeInfobar = 20
			self.eventFontSizeInfobar = 20

		self.listHeight = None
		self.listWidth = None
		self.serviceBorderWidth = 1
		self.serviceNamePadding = 3
		self.serviceNumberPadding = 9
		self.eventBorderWidth = 1
		self.eventNamePadding = 3
		self.NumberOfRows = None
		self.serviceNumberWidth = 0

	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			attribs = [ ]
			for (attrib, value) in self.skinAttributes:
				if attrib == "ServiceFontGraphical":
					font = parseFont(value, ((1,1),(1,1)) )
					self.serviceFontNameGraph = font.family
					self.serviceFontSizeGraph = font.pointSize
				elif attrib == "EntryFontGraphical":
					font = parseFont(value, ((1,1),(1,1)) )
					self.eventFontNameGraph = font.family
					self.eventFontSizeGraph = font.pointSize
				elif attrib == "ServiceFontInfobar":
					font = parseFont(value, ((1,1),(1,1)) )
					self.serviceFontNameInfobar = font.family
					self.serviceFontSizeInfobar = font.pointSize
				elif attrib == "EventFontInfobar":
					font = parseFont(value, ((1,1),(1,1)) )
					self.eventFontNameInfobar = font.family
					self.eventFontSizeInfobar = font.pointSize
				elif attrib == "EventFontSingle":
					font = parseFont(value, ((1,1),(1,1)) )
					self.eventFontNameSingle = font.family
					self.eventFontSizeSingle = font.pointSize

				elif attrib == "ServiceForegroundColor":
					self.foreColorService = parseColor(value).argb()
				elif attrib == "ServiceForegroundColorNow":
					self.foreColorServiceNow = parseColor(value).argb()
				elif attrib == "ServiceBackgroundColor":
					self.backColorService = parseColor(value).argb()
				elif attrib == "ServiceBackgroundColorNow":
					self.backColorServiceNow = parseColor(value).argb()

				elif attrib == "EntryForegroundColor":
					self.foreColor = parseColor(value).argb()
				elif attrib == "EntryForegroundColorSelected":
					self.foreColorSelected = parseColor(value).argb()
				elif attrib == "EntryBackgroundColor":
					self.backColor = parseColor(value).argb()
				elif attrib == "EntryBackgroundColorSelected":
					self.backColorSelected = parseColor(value).argb()
				elif attrib == "EntryBackgroundColorNow":
					self.backColorNow = parseColor(value).argb()
				elif attrib == "EntryBackgroundColorNowSelected":
					self.backColorNowSelected = parseColor(value).argb()
				elif attrib == "EntryForegroundColorNow":
					self.foreColorNow = parseColor(value).argb()
				elif attrib == "EntryForegroundColorNowSelected":
					self.foreColorNowSelected = parseColor(value).argb()

				elif attrib == "ServiceBorderColor":
					self.borderColorService = parseColor(value).argb()
				elif attrib == "ServiceBorderWidth":
					self.serviceBorderWidth = int(value)
				elif attrib == "ServiceNamePadding":
					self.serviceNamePadding = int(value)
				elif attrib == "ServiceNumberPadding":
					self.serviceNumberPadding = int(value)
				elif attrib == "EntryBorderColor":
					self.borderColor = parseColor(value).argb()
				elif attrib == "EventBorderWidth":
					self.eventBorderWidth = int(value)
				elif attrib == "EventNamePadding":
					self.eventNamePadding = int(value)

				elif attrib == "RecordForegroundColor":
					self.foreColorRecord = parseColor(value).argb()
				elif attrib == "RecordForegroundColorSelected":
					self.foreColorRecordSelected = parseColor(value).argb()
				elif attrib == "RecordBackgroundColor":
					self.backColorRecord = parseColor(value).argb()
				elif attrib == "RecordBackgroundColorSelected":
					self.backColorRecordSelected = parseColor(value).argb()
				elif attrib == "ZapForegroundColor":
					self.foreColorZap = parseColor(value).argb()
				elif attrib == "ZapBackgroundColor":
					self.backColorZap = parseColor(value).argb()
				elif attrib == "ZapForegroundColorSelected":
					self.foreColorZapSelected = parseColor(value).argb()
				elif attrib == "ZapBackgroundColorSelected":
					self.backColorZapSelected = parseColor(value).argb()
				elif attrib == "NumberOfRows":
					self.NumberOfRows = int(value)
				else:
					attribs.append((attrib,value))
			self.skinAttributes = attribs
		rc = GUIComponent.applySkin(self, desktop, screen)
		self.listHeight = self.instance.size().height()
		self.listWidth = self.instance.size().width()
		self.setFontsize()

		return rc

	def getCurrentChangeCount(self):
		return 0

	def setCurrentlyPlaying(self, serviceref):
		self.currentlyPlaying = serviceref

	def getEventFromId(self, service, eventid):
		event = None
		if self.epgcache is not None and eventid is not None:
			event = self.epgcache.lookupEventId(service.ref, eventid)
		return event

	def getIndexFromService(self, serviceref):
		if serviceref is not None:
			for x in range(len(self.list)):
				if CompareWithAlternatives(self.list[x][0], serviceref):
					return x
				if CompareWithAlternatives(self.list[x][1], serviceref):
					return x
		return None

	def getCurrentIndex(self):
		return self.instance.getCurrentIndex()

	def moveToService(self, serviceref):
		if not serviceref:
			return
		newIdx = self.getIndexFromService(serviceref)
		if newIdx is None:
			newIdx = 0
		self.setCurrentIndex(newIdx)

	def setCurrentIndex(self, index):
		if self.instance is not None:
			self.instance.moveSelectionTo(index)

	def moveTo(self, dir):
		if self.instance is not None:
			self.instance.moveSelection(dir)

	def getCurrent(self):
		# !EPG_TYPE_GRAPH and !EPG_TYPE_INFOBARGRAPH
		idx = 0
		if self.type == EPG_TYPE_MULTI:
			idx += 1
		tmp = self.l.getCurrentSelection()
		if tmp is None:
			return None, None
		eventid = tmp[idx+1]
		service = ServiceReference(tmp[idx])
		event = self.getEventFromId(service, eventid)
		return event, service

	def connectSelectionChanged(func):
		if not self.onSelChanged.count(func):
			self.onSelChanged.append(func)

	def disconnectSelectionChanged(func):
		self.onSelChanged.remove(func)

	def selectionChanged(self):
		for x in self.onSelChanged:
			if x is not None:
				x()

	GUI_WIDGET = eListbox

	def selectionEnabled(self, enabled):
		if self.instance is not None:
			self.instance.setSelectionEnable(enabled)

	def getPixmapForEntry(self, service, eventId, beginTime, duration):
		if not beginTime:
			return None
		rec = self.timer.isInTimer(eventId, beginTime, duration, service)
		if rec is not None:
			self.wasEntryAutoTimer = rec[2]
			return rec[1]
		else:
			self.wasEntryAutoTimer = False
			return None

	def queryEPG(self, list, buildFunc=None):
		if self.epgcache is not None:
			if buildFunc is not None:
				return self.epgcache.lookupEvent(list, buildFunc)
			else:
				return self.epgcache.lookupEvent(list)
		return [ ]

	def getCurrentCursorLocation(self):
		return self.time_base
