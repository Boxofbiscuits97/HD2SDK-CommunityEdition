from math import ceil
class StingrayStateMachine:
    # very complicated, only load the animation IDs from the state machine for now
    
    def __init__(self):
        self.animation_ids = []
        self.layer_count = self.layer_data_offset = self.animation_events_count = self.animation_events_offset = self.animation_vars_count = self.animation_vars_offset = 0
        self.blend_mask_count = self.blend_mask_offset = 0
        self.unk = self.unk2 = self.unk_data_00_offset = self.unk_data_00_size = self.unk_data_01_offset = self.unk_data_01_size = self.unk_data_02_offset = self.unk_data_02_size = 0
        self.pre_blend_mask_data = bytearray()
        self.post_blend_mask_data = bytearray()
        self.layers = []
        self.blend_masks = []
        self.blend_mask_offsets = []
        self.unk_data_03_size = self.unk_data_03_offset = 0
        self.unk_data_00 = None
        self.unk_data_01 = bytearray()
        self.unk_data_02 = bytearray()
        self.unk_data_03 = None
        self.ragdolls = []
        self.ragdoll_count = 0
        self.ragdoll_offset = 0
        
    def load(self, memory_stream):
        offset_start = memory_stream.tell()
        self.unk = memory_stream.uint32(self.unk)
        self.layer_count = memory_stream.uint32(self.layer_count)
        self.layer_data_offset = memory_stream.uint32(self.layer_data_offset)
        self.animation_events_count = memory_stream.uint32(self.animation_events_count)
        self.animation_events_offset = memory_stream.uint32(self.animation_events_offset)
        self.animation_vars_count = memory_stream.uint32(self.animation_vars_count)
        self.animation_vars_offset = memory_stream.uint32(self.animation_vars_offset)
        self.blend_mask_count = memory_stream.uint32(self.blend_mask_count)
        self.blend_mask_offset = memory_stream.uint32(self.blend_mask_offset) # blend masks are the only editable data for now
        
        self.unk_data_00_size = memory_stream.uint32(self.unk_data_00_size)
        self.unk_data_00_offset = memory_stream.uint32(self.unk_data_00_offset)
        self.unk_data_01_size = memory_stream.uint32(self.unk_data_01_size)
        self.unk_data_01_offset = memory_stream.uint32(self.unk_data_01_offset)
        self.unk_data_02_size = memory_stream.uint32(self.unk_data_02_size)
        self.unk_data_02_offset = memory_stream.uint32(self.unk_data_02_offset)
        self.unk_data_03_size = memory_stream.uint32(self.unk_data_03_size)
        self.unk_data_03_offset = memory_stream.uint32(self.unk_data_03_offset)
        
        self.ragdoll_count = memory_stream.uint32(self.ragdoll_count)
        self.ragdoll_offset = memory_stream.uint32(self.ragdoll_offset)
        
        if self.blend_mask_offset != 0:
            self.pre_blend_mask_data = memory_stream.read(self.blend_mask_offset - (memory_stream.tell() - offset_start))
        elif self.unk_data_00_offset != 0:
            self.pre_blend_mask_data = memory_stream.read(self.unk_data_00_offset - (memory_stream.tell() - offset_start))
        elif self.unk_data_01_offset != 0:
            self.pre_blend_mask_data = memory_stream.read(self.unk_data_01_offset - (memory_stream.tell() - offset_start))
        elif self.unk_data_02_offset != 0:
            self.pre_blend_mask_data = memory_stream.read(self.unk_data_02_offset - (memory_stream.tell() - offset_start))
        elif self.unk_data_03_offset != 0:
            self.pre_blend_mask_data = memory_stream.read(self.unk_data_03_offset - (memory_stream.tell() - offset_start))
        elif self.ragdoll_offset != 0:
            self.pre_blend_mask_data = memory_stream.read(self.ragdoll_offset - (memory_stream.tell() - offset_start))
        else:
            print("ERROR LOADING STATE MACHINE") # unknown length for state machine file, will not be able to load properly without length data
        
        # get layers
        memory_stream.seek(offset_start + self.layer_data_offset)
        self.layer_count = memory_stream.uint32(self.layer_count)
        layer_offsets = [memory_stream.uint32(t) for t in range(self.layer_count)]
        for offset in layer_offsets:
            layer_offset = offset_start + self.layer_data_offset + offset
            memory_stream.seek(layer_offset)
            new_layer = Layer()
            new_layer.load(memory_stream)
            self.layers.append(new_layer)
            
        # get blend masks
        if self.blend_mask_count > 0:
            memory_stream.seek(offset_start + self.blend_mask_offset)
            self.blend_mask_count = memory_stream.uint32(self.blend_mask_count)
            self.blend_mask_offsets = [memory_stream.uint32(t) for t in range(self.blend_mask_count)]
            for offset in self.blend_mask_offsets:
                memory_stream.seek(offset_start + self.blend_mask_offset + offset)
                new_blend_mask = BlendMask()
                new_blend_mask.load(memory_stream)
                self.blend_masks.append(new_blend_mask)
                
        # get unk data 00
        if self.unk_data_00_size > 0:
            memory_stream.seek(offset_start + self.unk_data_00_offset)
            item = Unk00Item()
            item.load(memory_stream)
            self.unk_data_00 = item
        
        # get unk data 01
        if self.unk_data_01_size > 0:
            memory_stream.seek(offset_start + self.unk_data_01_offset)
            self.unk_data_01 = memory_stream.read(self.unk_data_01_size)
        
        # get unk data 02
        if self.unk_data_02_size > 0:
            memory_stream.seek(offset_start + self.unk_data_02_offset)
            self.unk_data_02 = memory_stream.read(self.unk_data_02_size)
        
        # get unk data 03
        if self.unk_data_03_size > 0:
            memory_stream.seek(offset_start + self.unk_data_03_offset)
            item = Unk03Item()
            item.load(memory_stream)
            self.unk_data_03 = item
        
        # get ragdolls
        if self.ragdoll_count > 0:
            memory_stream.seek(offset_start + self.ragdoll_offset)
            for _ in range(self.ragdoll_count):
                new_ragdoll = RagdollItem()
                new_ragdoll.load(memory_stream)
                self.ragdolls.append(new_ragdoll)
            
        for layer in self.layers:
            for state in layer.states:
                for animation_id in state.animation_ids:
                    if animation_id not in self.animation_ids:
                        self.animation_ids.append(animation_id)

    def save(self, memory_stream):
        offset_start = memory_stream.tell()
        self.unk = memory_stream.uint32(self.unk)
        self.layer_count = memory_stream.uint32(self.layer_count)
        self.layer_data_offset = memory_stream.uint32(self.layer_data_offset)
        self.animation_events_count = memory_stream.uint32(self.animation_events_count)
        self.animation_events_offset = memory_stream.uint32(self.animation_events_offset)
        self.animation_vars_count = memory_stream.uint32(self.animation_vars_count)
        self.animation_vars_offset = memory_stream.uint32(self.animation_vars_offset)
        self.blend_mask_count = memory_stream.uint32(self.blend_mask_count)
        self.blend_mask_offset = memory_stream.uint32(self.blend_mask_offset) # blend masks are the only editable data for now
        
        self.unk_data_00_size = memory_stream.uint32(self.unk_data_00_size)
        self.unk_data_00_offset = memory_stream.uint32(self.unk_data_00_offset)
        self.unk_data_01_size = memory_stream.uint32(self.unk_data_01_size)
        self.unk_data_01_offset = memory_stream.uint32(self.unk_data_01_offset)
        self.unk_data_02_size = memory_stream.uint32(self.unk_data_02_size)
        self.unk_data_02_offset = memory_stream.uint32(self.unk_data_02_offset)
        self.unk_data_03_size = memory_stream.uint32(self.unk_data_03_size)
        self.unk_data_03_offset = memory_stream.uint32(self.unk_data_03_offset)
        
        self.ragdoll_count = memory_stream.uint32(self.ragdoll_count)
        self.ragdoll_offset = memory_stream.uint32(self.ragdoll_offset)
        
        memory_stream.write(self.pre_blend_mask_data)
            
        # save blend masks
        self.blend_mask_count = memory_stream.uint32(self.blend_mask_count)
        for offset in self.blend_mask_offsets:
            offset = memory_stream.uint32(offset)
        for i, blend_mask in enumerate(self.blend_masks):
            self.blend_mask_offsets[i] = memory_stream.tell() - offset_start - self.blend_mask_offset
            blend_mask.save(memory_stream)
            
        # save unk data 00
        if self.unk_data_00_size > 0:
            self.unk_data_00_offset = memory_stream.tell() - offset_start
            self.unk_data_00.save(memory_stream)
        
        # save unk data 01
        if self.unk_data_01_size > 0:
            self.unk_data_01_offset = memory_stream.tell() - offset_start
            memory_stream.write(self.unk_data_01)
        
        # save unk data 02
        if self.unk_data_02_size > 0:
            if memory_stream.tell() % 8 != 0:
                memory_stream.seek(memory_stream.tell() + 4)
            self.unk_data_02_offset = memory_stream.tell() - offset_start
            memory_stream.write(self.unk_data_02)
        
        # save unk data 03
        if self.unk_data_03_size > 0:
            self.unk_data_03_offset = memory_stream.tell() - offset_start
            self.unk_data_03.save(memory_stream)
            
        # save ragdolls
        if self.ragdoll_count > 0:
            self.ragdoll_offset = memory_stream.tell() - offset_start
            for ragdoll in self.ragdolls:
                ragdoll.save(memory_stream)
                
    def Serialize(self, memory_stream):
        if memory_stream.IsReading():
            self.load(memory_stream)
        else:
            start = memory_stream.tell()
            self.save(memory_stream)
            
            # redo saving with updated offsets (can maybe make this better)
            memory_stream.seek(start)
            self.save(memory_stream)
            
    def set_ragdoll(self, bone_index, params):
        new_ragdoll = RagdollItem()
        new_ragdoll.params = params
        new_ragdoll.bone_index = bone_index
        self.ragdoll_count += 1
        self.ragdolls.append(new_ragdoll)
        
    def remove_ragdoll(self, bone_index):
        idx = -1
        for i, ragdoll in enumerate(self.ragdolls):
            if ragdoll.bone_index == bone_index:
                idx = i
                break
        if idx != -1:
            self.ragdolls.pop(idx)
            self.ragdoll_count -= 1
        
class Layer:
    
    def __init__(self):
        self.magic = self.default_state = self.num_states = 0
        self.state_offsets = []
        self.states = []
    
    def load(self, memory_stream):
        offset_start = memory_stream.tell()
        self.magic = memory_stream.uint32(self.magic)
        self.default_state = memory_stream.uint32(self.default_state)
        self.num_states = memory_stream.uint32(self.num_states)
        self.state_offsets = [memory_stream.uint32(t) for t in range(self.num_states)]
        for state_offset in self.state_offsets:
            memory_stream.seek(offset_start + state_offset)
            new_state = State()
            new_state.load(memory_stream)
            self.states.append(new_state)
    
    def save(self, memory_stream): # unused
        offset_start = memory_stream.tell()
        self.magic = memory_stream.uint32(self.magic)
        self.default_state = memory_stream.uint32(self.default_state)
        self.num_states = memory_stream.uint32(self.num_states)
        self.state_offsets = [memory_stream.uint32(t) for t in self.state_offsets]
        for i, state in enumerate(self.states):
            self.state_offsets[i] = (memory_stream.tell() - offset_start)
            state.save(memory_stream)
    
class State:
    
    def __init__(self):
        self.name = self.state_type = self.animation_count = self.animation_offset = self.blend_mask_index = 0
        self.animation_ids = []
    
    def load(self, stream):
        offset_start = stream.tell()
        self.name = stream.uint64(self.name)
        self.state_type = stream.uint32(self.state_type)
        self.animation_count = stream.uint32(self.animation_count)
        self.animation_offset = stream.uint32(self.animation_offset)
        
        stream.seek(stream.tell() + 88) # skip all that other stuff for now
        self.blend_mask_index = stream.uint32(self.blend_mask_index) # I assume 0xFFFFFFFF means no mask
        
        stream.seek(offset_start + self.animation_offset)
        self.animation_ids = [stream.uint64(t) for t in range(self.animation_count)]
    
class BlendMask:
    
    def __init__(self):
        self.bone_count = 0
        self.bone_weights = []
        
    def load(self, stream):
        self.bone_count = stream.uint32(self.bone_count)
        self.bone_weights = [stream.float32(t) for t in range(self.bone_count)]
        
    def save(self, stream):
        self.bone_count = stream.uint32(self.bone_count)
        self.bone_weights = [stream.float32(w) for w in self.bone_weights]
        
class RagdollItem:
    
    def __init__(self):
        self.bone_index = 0
        self.params = [0] * 9
        self.unk_hash = 0
        self.unk_enum = 2
        self.unk = 0
        
    def load(self, stream):
        self.bone_index = stream.uint32(self.bone_index)
        self.params = [stream.float32(t) for t in range(9)]
        self.unk_hash = stream.uint64(self.unk_hash)
        self.unk_enum = stream.uint32(self.unk_enum)
        self.unk = stream.uint32(self.unk)
        
    def save(self, stream):
        self.bone_index = stream.uint32(self.bone_index)
        self.params = [stream.float32(f) for f in self.params]
        self.unk_hash = stream.uint64(self.unk_hash)
        self.unk_enum = stream.uint32(self.unk_enum)
        self.unk = stream.uint32(self.unk)
        
class Unk00Item:
    
    def __init__(self):
        self.count = 0
        self.data = bytearray()
        
    def load(self, stream):
        self.count = stream.uint32(self.count)
        self.data = stream.read(16 * self.count)
        
    def save(self, stream):
        self.count = stream.uint32(self.count)
        stream.write(self.data)
        
class Unk03ItemSection:
    
    def __init__(self):
        self.size = 0
        self.unk = 0
        self.data = [bytearray(), bytearray()]
        self.offsets = [0, 0]
        self.counts = [0, 0]
        
    def load(self, stream):
        start_offset = stream.tell()
        self.unk = stream.uint64(self.unk)
        self.counts[0] =  stream.uint16(0)
        self.offsets[0] = stream.uint16(0)
        self.counts[1] =  stream.uint16(0)
        self.offsets[1] = stream.uint16(0)
        if self.counts[0] > 0:
            stream.seek(start_offset + self.offsets[0])
            self.data[0] = stream.read(4*self.counts[0])
        if self.counts[1] > 0:
            stream.seek(start_offset + self.offsets[1])
            self.data[1] = stream.read(4*self.counts[1])

    # to-do: update offsets if this is ever allowed to be edited
    def save(self, stream):
        self.unk = stream.uint64(self.unk)
        _ = stream.uint16(self.counts[0])
        _ = stream.uint16(self.offsets[0])
        _ = stream.uint16(self.counts[1])
        _ = stream.uint16(self.offsets[1])
        if self.counts[0] > 0:
            _ = stream.write(self.data[0])
        if self.counts[1] > 0:
            _ = stream.write(self.data[1])
        
class Unk03Item:
    
    def __init__(self):
        self.count = 0
        self.section_offsets = []
        self.sections = []
        
    def load(self, stream):
        start_offset = stream.tell()
        self.count = stream.uint32(self.count)
        self.sections = [None] * self.count
        self.section_offsets = [0] * self.count
        for i in range(self.count):
            self.section_offsets[i] = stream.uint32(0)
        for i in range(self.count):
            stream.seek(start_offset + self.section_offsets[i])
            section = Unk03ItemSection()
            section.load(stream)
            self.sections[i] = section

    # to-do: update offsets if this is ever allowed to be edited    
    def save(self, stream):
        start_offset = stream.tell()
        self.count = stream.uint32(self.count)
        for offset in self.section_offsets:
            _ = stream.uint32(offset)
        for i, section in enumerate(self.sections):
            stream.seek(start_offset + self.section_offsets[i])
            section.save(stream)