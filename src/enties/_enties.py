from dataclasses import dataclass,asdict as B,astuple as C,fields as L,is_dataclass as M
from typing import get_type_hints as N,get_origin as O,get_args as P

@dataclass
class Data:
	@classmethod
	def parse(F,data:dict):
		C=data;D='parse';H,I,J=hasattr,getattr,M
		if not isinstance(C,dict):return C
		Q=N(F);K={}
		for R in L(F):
			E=R.name
			if E not in C:continue
			A=C[E];B=Q.get(E);S=O(B)
			if S is list:
				G=P(B)[0]
				if J(G)and H(G,D):A=[I(G,D)(A)for A in A]
			elif J(B)and H(B,D):A=I(B,D)(A)
			K[E]=A
		return F(**K)
	def asdict(A):return B(A)
	def astuple(A):return C(A)
@dataclass
class Range(Data):
	target:float=0;duration:float=0
	@staticmethod
	def timestamp(range:'Range'):return Timestamp.range(range.target, range.target+range.duration)
@dataclass
class Timestamp(Data):
	start:float=0;end:float=0
	@staticmethod
	def range(timestamp:'Timestamp'):return Range.timestamp(timestamp.start, timestamp.end-timestamp.start)
@dataclass
class Transcribe(Timestamp):text:str=None