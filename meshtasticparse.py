import re
import os

def parse_meshtastic_data(file_path, printindex=1):
    # IDs as they appear in the Meshtastic log
    BOAT_ID = "-614960848"
    BUOY_ID = "-1628647980"

    # A single master list to hold all valid readings before sorting
    all_packets = []

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split the file by the start of each packet's timestamp block
    packet_blocks = re.split(r'(?=\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M\s+\[Packet\])', content)

    for block in packet_blocks:
        if not block.strip():
            continue
            
        # 1. Extract block timestamp
        ts_match = re.search(r'^(\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M)\s+\[Packet\]', block)
        if not ts_match:
            continue
        timestamp = ts_match.group(1)

        # 2. Extract from_id
        from_match = re.search(r'from=([-0-9]+)', block)
        if not from_match:
            continue
        from_id = from_match.group(1)

        # Only process if it's our target boat or buoy 
        if from_id not in (BOAT_ID, BUOY_ID):
            continue

        # 3. Extract latitude and longitude FIRST
        lat_match = re.search(r'latitude_i=([-0-9]+)', block)
        lon_match = re.search(r'longitude_i=([-0-9]+)', block)
        
        # SKIP THIS READING completely if it doesn't have location data
        if not lat_match or not lon_match:
            continue

        # 4. Extract rx_time, time, and sats_in_view
        # Grab rx_time from the MeshPacket header
        rx_time_match = re.search(r'rx_time=([0-9]+)', block)
        
        # Use negative lookbehind (?<!rx_) to ensure we don't accidentally match the "time=" inside "rx_time="
        time_match = re.search(r'(?<!rx_)time=([0-9]+)', block)
        
        # Extract sats_in_view
        sats_match = re.search(r'sats_in_view=([0-9]+)', block)
        
        rx_time_str = rx_time_match.group(1) if rx_time_match else "NaN"
        packet_time = time_match.group(1) if time_match else "NaN"
        sats_in_view = sats_match.group(1) if sats_match else "NaN"
        
        # We need this as an integer for the sorting math to work (fallback to 0 if missing)
        rx_time_int = int(rx_time_match.group(1)) if rx_time_match else 0 
        
        lat = str(int(lat_match.group(1)) / 1e7)
        lon = str(int(lon_match.group(1)) / 1e7)

        # Append to master list with a 'node' tag identifying the source
        all_packets.append({
            'node': 'boat' if from_id == BOAT_ID else 'buoy',
            'rx_time_int': rx_time_int, # Integer used strictly for sorting
            'timestamp': timestamp,
            'rx_time': rx_time_str,
            'time': packet_time,
            'latitude': lat,
            'longitude': lon,
            'sats_in_view': sats_in_view
        })

    # 5. SORT globally by the rx_time integer in descending order (highest/newest time first)
    all_packets.sort(key=lambda x: x['rx_time_int'], reverse=True)

    # 6. Assign indices to the chronologically sorted timeline and split the lists
    boat_packets = []
    buoy_packets = []
    
    global_index = 1
    for p in all_packets:
        p['index'] = global_index
        if p['node'] == 'boat':
            boat_packets.append(p)
        else:
            buoy_packets.append(p)
        global_index += 1

    # Helper function to generate and write the feature arrays
    def write_node_data(packets, prefix):
        if not packets:
            print(f"No packets found for {prefix}.")
            return
        
        # The features we want to extract into separate files (now includes sats_in_view)
        features = ['timestamp', 'rx_time', 'time', 'latitude', 'longitude', 'sats_in_view']

        print(f"Writing {prefix.capitalize()} files...")
        
        for feature in features:
            filename = f'{prefix}_{feature}.txt'
            with open(filename, 'w', encoding='utf-8') as f:
                if printindex == 1:
                    # Format each line as "Index FeatureValue" (e.g., "1 32.91242")
                    lines = [f"{p['index']} {p[feature]}" for p in packets]
                else:
                    # Format each line as just "FeatureValue" (e.g., "32.91242")
                    lines = [f"{p[feature]}" for p in packets]
                    
                f.write('\n'.join(lines))
            print(f" -> Created {filename}")

    # 7. Export the data 
    write_node_data(boat_packets, 'boat')
    write_node_data(buoy_packets, 'buoy')

    print("\nData extraction complete! Measurements sorted by rx_time with newest reading first.")

# ---------------------------------------------------------
# Set this to 1 to include the index, or 0 to omit the index
PRINT_INDEX_SETTING = 0
# ---------------------------------------------------------

# Run the function on the provided file
parse_meshtastic_data('meshtastic_debug_20260510_135242WALKINGAROUND3BOAT.txt', printindex=PRINT_INDEX_SETTING)
