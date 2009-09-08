import time
import struct
import socket

# Some zeroconf constants
LOCAL_NAME = ".local."

# Some timing constants

UNREGISTER_TIME = 125
CHECK_TIME = 175
REGISTER_TIME = 225
LISTENER_TIME = 200
BROWSER_TIME = 500

# Some DNS constants
    
MDNS_ADDR = '224.0.0.251'
MDNS_PORT = 5353;
DNS_PORT = 53;
DNS_TTL = 60 * 60; # one hour default TTL

MAX_MSG_TYPICAL = 1460 # unused
MAX_MSG_ABSOLUTE = 8972

FLAGS_QR_MASK = 0x8000 # query response mask
FLAGS_QR_QUERY = 0x0000 # query
FLAGS_QR_RESPONSE = 0x8000 # response

FLAGS_AA = 0x0400 # Authorative answer
FLAGS_TC = 0x0200 # Truncated
FLAGS_RD = 0x0100 # Recursion desired
FLAGS_RA = 0x8000 # Recursion available

FLAGS_Z = 0x0040 # Zero
FLAGS_AD = 0x0020 # Authentic data
FLAGS_CD = 0x0010 # Checking disabled

CLASS_IN = 1
CLASS_CS = 2
CLASS_CH = 3
CLASS_HS = 4
CLASS_NONE = 254
CLASS_ANY = 255
CLASS_MASK = 0x7FFF
CLASS_UNIQUE = 0x8000

TYPE_A = 1
TYPE_NS = 2
TYPE_MD = 3
TYPE_MF = 4
TYPE_CNAME = 5
TYPE_SOA = 6
TYPE_MB = 7
TYPE_MG = 8
TYPE_MR = 9
TYPE_NULL = 10
TYPE_WKS = 11
TYPE_PTR = 12
TYPE_HINFO = 13
TYPE_MINFO = 14
TYPE_MX = 15
TYPE_TXT = 16
TYPE_AAAA = 28
TYPE_SRV = 33
TYPE_ANY =  255

NAME_ANY = 255

# Mapping constants to names
CLASSES = { CLASS_IN : "in",
            CLASS_CS : "cs",
            CLASS_CH : "ch",
            CLASS_HS : "hs",
            CLASS_NONE : "none",
            CLASS_ANY : "any" }

TYPES = { TYPE_A : "a",
          TYPE_NS : "ns",
          TYPE_MD : "md",
          TYPE_MF : "mf",
          TYPE_CNAME : "cname",
          TYPE_SOA : "soa",
          TYPE_MB : "mb",
          TYPE_MG : "mg",
          TYPE_MR : "mr",
          TYPE_NULL : "null",
          TYPE_WKS : "wks",
          TYPE_PTR : "ptr",
          TYPE_HINFO : "hinfo",
          TYPE_MINFO : "minfo",
          TYPE_MX : "mx",
          TYPE_TXT : "txt",
          TYPE_AAAA : "quada",
          TYPE_SRV : "srv",
          TYPE_ANY : "any" }

# Exceptions

class NonLocalNameException(Exception):
    pass

class NonUniqueNameException(Exception):
    pass

class NamePartTooLongException(Exception):
    pass

class AbstractMethodException(Exception):
    pass

class BadTypeInNameException(Exception):
    pass

# helpers
def now():
    return time.time() * 1000

# impl

class DNSEntry(object):
    def __init__(self, name, type_, class_):
        self.key = name.lower()
        self.name = name
        self._type = type_
        self._class = class_ & CLASS_MASK
        self.unique = (class_ & CLASS_UNIQUE) != 0
    
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (self.name == other.name and self.class_ == other.class_
                    and self.type == other.type)
        return 0

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.name, self.class_, self.type))

    @property
    def type(self):
        return TYPES[self._type]

    @property
    def class_(self):
        return CLASSES[self._class]

class DNSQuestion(DNSEntry):
    def __init__(self, name, type_, class_=CLASS_IN):
        if not name.endswith(LOCAL_NAME):
            raise NonLocalNameException
        super(DNSQuestion, self).__init__(name, type_, class_)
    def answeredBy(self, record):
        return ((self.class_ == record.class_ or self.class_ == CLASS_ANY)
                and (self.name == record.name or self.name == NAME_ANY)
                and (self.type == record.type or self._type == TYPE_ANY))

class DNSRecord(DNSEntry):
    def __init__(self, name, type_, class_, ttl):
        super(DNSRecord, self).__init__(name, type_, class_)
        self.ttl = ttl * 1000
        self.created = now()
    def isExpired(self, when):
        return (self.created + self.ttl) <= when
    def isStale(self, when):
        return (self.created + (.5 * self.ttl)) <= when
    def update(self, other):
        self.created = other.created
        self.ttl = other.ttl
    
class DNSAddress(DNSRecord):
    def __init__(self, name, type_, class_, ttl, address):
        super(DNSAddress, self).__init__(name, type_, class_, ttl)
        self._address = address
    
    @property
    def address(self):
        try:
            return socket.inet_ntoa(self._address)
        except:
            return self._address
    
    def __eq__(self, other):
        if super(self.__class__, self).__eq__(other):
            return (self.address == other.address)
        return 0
    def __hash__(self):
        return hash((self.name, self.class_, self.type, self.address))
    
class DNSHinfo(DNSRecord):
    def __init__(self, name, type_, class_, ttl, cpu, os):
        super(DNSHinfo, self).__init__(name, type_, class_, ttl)
        self.cpu = cpu
        self.os = os
    def __eq__(self, other):
        if super(self.__class__, self).__eq__(other):
            return (self.cpu == other.cpu and self.os == other.os)
        return 0
    def __hash__(self):
        return hash((self.name, self.class_, self.type, self.os, self.cpu))

class DNSPointer(DNSRecord):
    def __init__(self, name, type_, class_, ttl, alias):
        super(DNSPointer, self).__init__(name, type_, class_, ttl)
        self.alias = alias
    def __eq__(self, other):
        if super(self.__class__, self).__eq__(other):
            return (self.alias == other.alias)
        return 0
    def __hash__(self):
        return hash((self.name, self.class_, self.type, self.alias))

class DNSText(DNSRecord):
    def __init__(self, name, type_, class_, ttl, text):
        super(DNSText, self).__init__(name, type_, class_, ttl)
        self.text = text
    
    def __eq__(self, other):
        if super(self.__class__, self).__eq__(other):
            return (self.text == other.text)
        return 0
    def __hash__(self):
        return hash((self.name, self.class_, self.type, self.text))

class DNSService(DNSRecord):
    def __init__(self, name, type_, class_, ttl, priority, weight, port, server):
        super(DNSService, self).__init__(name, type_, class_, ttl)
        self.priority = priority
        self.weight = weight
        self.port = port
        self.server = server
    def __eq__(self, other):
        if super(self.__class__, self).__eq__(other):
            return (self.priority == other.priority and self.weight == other.weight and
                    self.port == other.port and self.server == other.server)
        return 0
    def __hash__(self):
        return hash((self.name, self.class_, self.type,
                     self.priority, self.weight, self.port,
                     self.server))

class DNSIncoming(object):
    def __init__(self, data=None):
        self.offset = 0
        self.questions = []
        self.answers = []
        self.numQuestions = 0
        self.numAnswers = 0
        self.numAuthorities = 0
        self.numAdditionals = 0
        
        self.data = data
        if self.data:
            self.readHeader()
            self.readQuestions()
            self.readOthers()
    
    @classmethod
    def parse(cls, data):
        packet = cls(data)
        return packet

    def readHeader(self):
        """Reads header portion of packet"""
        format = '!HHHHHH'
        length = struct.calcsize(format)
        info = struct.unpack(format, self.data[self.offset:self.offset+length])
        self.offset += length

        self.id = info[0]
        self.flags = info[1]
        self.numQuestions = info[2]
        self.numAnswers = info[3]
        self.numAuthorities = info[4]
        self.numAdditionals = info[5]
    def readQuestions(self):
        """Reads questions section of packet"""
        format = '!HH'
        length = struct.calcsize(format)
        for i in range(0, self.numQuestions):
            name = self.readName()
            info = struct.unpack(format, self.data[self.offset:self.offset+length])
            self.offset += length
            
            question = DNSEntry(name, info[0], info[1])
            self.questions.append(question)
    def readOthers(self):
        """Reads the answers, authorities and additionals section of the packet"""
        format = '!HHiH'
        length = struct.calcsize(format)
        n = self.numAnswers + self.numAuthorities + self.numAdditionals
        for i in range(0, n):
            domain = self.readName()
            info = struct.unpack(format, self.data[self.offset:self.offset+length])
            self.offset += length

            rec = None
            if info[0] == TYPE_A:
                rec = DNSAddress(domain, info[0], info[1], info[2], self.readString(4))
            elif info[0] == TYPE_CNAME or info[0] == TYPE_PTR:
                rec = DNSPointer(domain, info[0], info[1], info[2], self.readName())
            elif info[0] == TYPE_TXT:
                rec = DNSText(domain, info[0], info[1], info[2], self.readString(info[3]))
            elif info[0] == TYPE_SRV:
                rec = DNSService(domain, info[0], info[1], info[2], self.readUnsignedShort(), self.readUnsignedShort(), self.readUnsignedShort(), self.readName())
            elif info[0] == TYPE_HINFO:
                rec = DNSHinfo(domain, info[0], info[1], info[2], self.readCharacterString(), self.readCharacterString())
            elif info[0] == TYPE_AAAA:
                rec = DNSAddress(domain, info[0], info[1], info[2], self.readString(16))
            else:
                # Try to ignore types we don't know about
                # this may mean the rest of the name is
                # unable to be parsed, and may show errors
                # so this is left for debugging.  New types
                # encountered need to be parsed properly.
                #
                #print "UNKNOWN TYPE = " + str(info[0])
                #raise BadTypeInNameException
                pass

            if rec is not None:
                self.answers.append(rec)

    def readInt(self):
        """Reads an integer from the packet"""
        format = '!I'
        length = struct.calcsize(format)
        info = struct.unpack(format, self.data[self.offset:self.offset+length])
        self.offset += length
        return info[0]
    def readCharacterString(self):
        """Reads a character string from the packet"""
        length = ord(self.data[self.offset])
        self.offset += 1
        return self.readString(length)
    def readString(self, len):
        """Reads a string of a given length from the packet"""
        format = '!' + str(len) + 's'
        length =  struct.calcsize(format)
        info = struct.unpack(format, self.data[self.offset:self.offset+length])
        self.offset += length
        return info[0]
    def readUnsignedShort(self):
        """Reads an unsigned short from the packet"""
        format = '!H'
        length = struct.calcsize(format)
        info = struct.unpack(format, self.data[self.offset:self.offset+length])
        self.offset += length
        return info[0]
    def readUTF(self, offset, len):
        """Reads a UTF-8 string of a given length from the packet"""
        result = self.data[offset:offset+len].decode('utf-8')
        return result
    def readName(self):
        """Reads a domain name from the packet"""
        result = ''
        off = self.offset
        next = -1
        first = off

        while 1:
            len = ord(self.data[off])
            off += 1
            if len == 0:
                break
            t = len & 0xC0
            if t == 0x00:
                result = ''.join((result, self.readUTF(off, len) + '.'))
                off += len
            elif t == 0xC0:
                if next < 0:
                    next = off + 1
                off = ((len & 0x3F) << 8) | ord(self.data[off])
                if off >= first:
                    raise "Bad domain name (circular) at " + str(off)
                first = off
            else:
                raise "Bad domain name at " + str(off)

        if next >= 0:
            self.offset = next
        else:
            self.offset = off

        return result
    
    def isQuery(self):
        """Returns true if this is a query"""
        return (self.flags & FLAGS_QR_MASK) == FLAGS_QR_QUERY
    def isResponse(self):
        """Returns true if this is a response"""
        return (self.flags & FLAGS_QR_MASK) == FLAGS_QR_RESPONSE

class DNSOutgoing(object):
	"""Object representation of an outgoing packet"""
	
	def __init__(self, flags, multicast = 1):
		self.finished = 0
		self.id = 0
		self.multicast = multicast
		self.flags = flags
		self.names = {}
		self.data = []
		self.size = 12
		
		self.questions = []
		self.answers = []
		self.authorities = []
		self.additionals = []

	def addQuestion(self, record):
		"""Adds a question"""
		self.questions.append(record)

	def addAnswer(self, inp, record):
		"""Adds an answer"""
		if not record.suppressedBy(inp):
			self.addAnswerAtTime(record, 0)

	def addAnswerAtTime(self, record, now):
		"""Adds an answer if if does not expire by a certain time"""
		if record is not None:
			if now == 0 or not record.isExpired(now):
				self.answers.append((record, now))

	def addAuthorativeAnswer(self, record):
		"""Adds an authoritative answer"""
		self.authorities.append(record)

	def addAdditionalAnswer(self, record):
		"""Adds an additional answer"""
		self.additionals.append(record)

	def writeByte(self, value):
		"""Writes a single byte to the packet"""
		format = '!c'
		self.data.append(struct.pack(format, chr(value)))
		self.size += 1

	def insertShort(self, index, value):
		"""Inserts an unsigned short in a certain position in the packet"""
		format = '!H'
		self.data.insert(index, struct.pack(format, value))
		self.size += 2
		
	def writeShort(self, value):
		"""Writes an unsigned short to the packet"""
		format = '!H'
		self.data.append(struct.pack(format, value))
		self.size += 2

	def writeInt(self, value):
		"""Writes an unsigned integer to the packet"""
		format = '!I'
		self.data.append(struct.pack(format, value))
		self.size += 4

	def writeString(self, value, length):
		"""Writes a string to the packet"""
		format = '!' + str(length) + 's'
		self.data.append(struct.pack(format, value))
		self.size += length

	def writeUTF(self, s):
		"""Writes a UTF-8 string of a given length to the packet"""
		utfstr = s.encode('utf-8')
		length = len(utfstr)
		if length > 64:
			raise NamePartTooLongException
		self.writeByte(length)
		self.writeString(utfstr, length)

	def writeName(self, name):
		"""Writes a domain name to the packet"""

		try:
			# Find existing instance of this name in packet
			#
			index = self.names[name]
		except KeyError:
			# No record of this name already, so write it
			# out as normal, recording the location of the name
			# for future pointers to it.
			#
			self.names[name] = self.size
			parts = name.split('.')
			if parts[-1] == '':
				parts = parts[:-1]
			for part in parts:
				self.writeUTF(part)
			self.writeByte(0)
			return

		# An index was found, so write a pointer to it
		#
		self.writeByte((index >> 8) | 0xC0)
		self.writeByte(index)

	def writeQuestion(self, question):
		"""Writes a question to the packet"""
		self.writeName(question.name)
		self.writeShort(question._type)
		self.writeShort(question._class)

	def writeRecord(self, record, now):
		"""Writes a record (answer, authoritative answer, additional) to
		the packet"""
		self.writeName(record.name)
		self.writeShort(record._type)
		if record.unique and self.multicast:
			self.writeShort(record._class | _CLASS_UNIQUE)
		else:
			self.writeShort(record._class)
		if now == 0:
			self.writeInt(record.ttl)
		else:
			self.writeInt(record.getRemainingTTL(now))
		index = len(self.data)
		# Adjust size for the short we will write before this record
		#
		self.size += 2
		record.write(self)
		self.size -= 2
		
		length = len(''.join(self.data[index:]))
		self.insertShort(index, length) # Here is the short we adjusted for

	def packet(self):
		"""Returns a string containing the packet's bytes

		No further parts should be added to the packet once this
		is done."""
		if not self.finished:
			self.finished = 1
			for question in self.questions:
				self.writeQuestion(question)
			for answer, time in self.answers:
				self.writeRecord(answer, time)
			for authority in self.authorities:
				self.writeRecord(authority, 0)
			for additional in self.additionals:
				self.writeRecord(additional, 0)
		
			self.insertShort(0, len(self.additionals))
			self.insertShort(0, len(self.authorities))
			self.insertShort(0, len(self.answers))
			self.insertShort(0, len(self.questions))
			self.insertShort(0, self.flags)
			if self.multicast:
				self.insertShort(0, 0)
			else:
				self.insertShort(0, self.id)
		return ''.join(self.data)

class Cache(object):
    """ we are going to emulate a list, more or less """
    def __init__(self):
        self._data = []
        self.questions = {}

    def addSubscription(self, question, subscriber):
        if question not in self.questions.keys():
            self.questions[question] = []
        self.questions[question].append(subscriber)

    def removeSubscription(self, question, subscriber):
        self.questions[question].remove(subscriber)

    def sweepCache(self, when=None):
        if not when:
            when = now()
        self._data = [d for d in self._data if not d.isExpired(when)]

    def update(self, new):
        old = self._data[self.index(new)]
        old.update(new)
        return old
    
    # list impl
    def append(self, record):
        self._data.append(record)
        for question in self.questions.keys():
            if question.answeredBy(record):
                for subscriber in self.questions[question]:
                    subscriber.recordAdded(record)

    def remove(self, record):
        self._data.remove(record)
        for question in self.questions.keys():
            if question.answeredBy(record):
                for subscriber in self.questions[question]:
                    subscriber.recordRemoved(record)

    def index(self, *args):
        return self._data.index(*args)

    def __len__(self):
        return self._data.__len__()

    def __getitem__(self, key):
        return self._data.__getitem__(key)
    
    def __setitem__(self, key, value):
        return self._data.__setitem__(key, value)

    def __delitem__(self, key):
        return self._data.__delitem__(key)

    def __iter__(self):
        return iter(self._data)
        
    
