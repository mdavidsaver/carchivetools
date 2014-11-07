from __future__ import print_function
import google.protobuf as protobuf
from carchive.pb import EPICSEvent_pb2 as pbt
from carchive.pb import escape as pb_escape
from carchive.pb import dtypes as pb_dtypes

class EmptyFileError(Exception):
    pass

class VerificationError(Exception):
    pass

def verify_stream(stream, pb_type=None, pv_name=None, year=None, upper_ts_bound=None):
    # Prepare line iterator.
    line_iterator = pb_escape.iter_lines(stream)
    
    # Check if we have a header.
    try:
        header_data = line_iterator.next()
    except pb_escape.IterationError as e:
        raise VerificationError('Reading header: {}'.format(e))
    except StopIteration:
        raise EmptyFileError()
    
    # Parse header.
    header_pb = pbt.PayloadInfo()
    try:
        header_pb.ParseFromString(header_data)
    except protobuf.message.DecodeError as e:
        raise VerificationError('Failed to decode header: {}'.format(e))
    
    # Sanity checks.
    if pb_type != None and header_pb.type != pb_type:
        raise VerificationError('Type mispatch in header')
    if pv_name != None and header_pb.pvname != pv_name:
        raise VerificationError('PV name mispatch in header')
    if year != None and header_pb.year != year:
        raise VerificationError('Year mispatch in header')
    
    # Find PB class for this data type.
    pb_class = pb_dtypes.get_pb_class_for_type(header_pb.type)
    
    # Will be returning the last timestamp (if any).
    last_timestamp = None
    
    # Iterate the file to the end, checking for problems.
    try:
        for sample_data in line_iterator:
            # Parse sample.
            sample_pb = pb_class()
            try:
                sample_pb.ParseFromString(sample_data)
            except protobuf.message.DecodeError as e:
                raise VerificationError('Failed to decode sample: {}'.format(e))
            
            # Sanity check timestamp.
            sample_timestamp = (sample_pb.secondsintoyear, sample_pb.nano)
            if upper_ts_bound is not None:
                if sample_timestamp > upper_ts_bound:
                    raise VerificationError('Found newer sample')
            
            last_timestamp = sample_timestamp
            
    except pb_escape.IterationError as e:
        raise VerificationError('Reading samples: {}'.format(e))
    
    return {
        'last_timestamp': last_timestamp,
        'year': header_pb.year,
    }
