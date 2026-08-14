from dataclasses import dataclass

@dataclass
class Timestamp:start:float;end:float

@dataclass
class Transcribe(Timestamp):text:str

@dataclass
class Audio(Transcribe):pitch:float=1.0;atempo:float=1.0;volume:float=1.0

@dataclass
class TrackAudio(Audio):
	sst:float=None
	snd:float=None
	def __post_init__(self):
		if self.sst is None: self.sst = self.start
		if self.snd is None: self.snd = self.end
