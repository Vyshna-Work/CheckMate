// React + hooks
import React, { useEffect, useState } from 'react';

// Basic UI components
import { 
  View, 
  Text, 
  StyleSheet, 
  TouchableOpacity, 
  ActivityIndicator,
  PermissionsAndroid,
  Platform
} from 'react-native';

import { CommonActions } from '@react-navigation/native';
import AsyncStorage from '@react-native-async-storage/async-storage';

//  Import your native module
import { NativeModules } from 'react-native';
const { BLEAdvertiser } = NativeModules;

import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RootStackParamList } from './App';
type HomeScreenNavigationProp = NativeStackNavigationProp<
  RootStackParamList,
  'Home'
>;

export default function HomeScreen({ navigation }: { navigation: HomeScreenNavigationProp }) {

  // Local state
  const [userId, setUserId] = useState<string | null>(null);
  const [bleId, setBleId] = useState<string | null>(null);
  const [name, setName] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [broadcasting, setBroadcasting] = useState(false);

  // Load user data from AsyncStorage
  useEffect(() => {
    const loadUserData = async () => {
      const storedUserId = await AsyncStorage.getItem("user_id");
      const storedBleId = await AsyncStorage.getItem("ble_id");
      const storedName = await AsyncStorage.getItem("name");
      
      setName(storedName);
      setUserId(storedUserId);
      setBleId(storedBleId);

      setLoading(false);
    };

    loadUserData();
  }, []);

  // Request BLE permissions (Android 12+)
  const requestBlePermissions = async () => {
    if (Platform.OS !== "android") return true;

    try {
      const granted = await PermissionsAndroid.requestMultiple([
        PermissionsAndroid.PERMISSIONS.BLUETOOTH_ADVERTISE,
        PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
      ]);

      return Object.values(granted).every(
        (status) => status === PermissionsAndroid.RESULTS.GRANTED
      );

    } catch (err) {
      console.warn(err);
      return false;
    }
  };

  //  Start BLE broadcasting using your native module
  const startBroadcasting = async () => {
    if (!bleId) return;

    const hasPermission = await requestBlePermissions();
    if (!hasPermission) {
      console.log("BLE permissions denied");
      return;
    }

    setBroadcasting(true);

    try {
      await BLEAdvertiser.startAdvertising(bleId);
      console.log("Broadcasting started");
    } catch (error) {
      console.log("BLE error:", error);
      setBroadcasting(false);
    }
  };

  //  Stop BLE broadcasting using your native module
  const stopBroadcasting = async () => {
    try {
      await BLEAdvertiser.stopAdvertising();
      setBroadcasting(false);
      console.log("Broadcasting stopped");
    } catch (error) {
      console.log("BLE stop error:", error);
    }
  };

  const handleLogout = async () => {
    await AsyncStorage.clear();

    // Stop advertising on logout
    try { await BLEAdvertiser.stopAdvertising(); } catch {}

    navigation.dispatch(
      CommonActions.reset({
        index: 0,
        routes: [{ name: "Landing" }],
      })
    );
  };

  // Loading screen
  if (loading) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="large" color="#007bff" />
        <Text style={styles.subtitle}>Loading your data...</Text>
      </View>
    );
  }

  // Main UI
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Welcome, {name}</Text>

      <Text style={styles.info}>Your BLE ID:</Text>
      <Text style={styles.ble}>{bleId}</Text>

      {!broadcasting ? (
        <TouchableOpacity style={styles.button} onPress={startBroadcasting}>
          <Text style={styles.buttonText}>Activate BLE Broadcasting</Text>
        </TouchableOpacity>
      ) : (
        <>
          <Text style={styles.broadcasting}>Broadcasting BLE Signal</Text>

          <TouchableOpacity 
            style={[styles.button, { backgroundColor: "red", marginTop: 20 }]} 
            onPress={stopBroadcasting}
          >
            <Text style={styles.buttonText}>Stop Broadcasting</Text>
          </TouchableOpacity>
        </>
      )}

      <TouchableOpacity 
        style={[styles.button, { backgroundColor: "#555", marginTop: 40 }]}
        onPress={handleLogout}>
        <Text style={styles.buttonText}>Logout</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'white',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    marginBottom: 20,
  },
  info: {
    fontSize: 20,
  },
  ble: {
    fontSize: 18,
    marginBottom: 30,
    color: '#007bff',
  },
  button: {
    padding: 15,
    backgroundColor: '#28a745',
    borderRadius: 10,
    width: '80%',
    alignItems: 'center',
  },
  buttonText: {
    color: 'white',
    fontSize: 18,
    fontWeight: 'bold',
  },
  broadcasting: {
    fontSize: 20,
    color: '#28a745',
    marginTop: 20,
  },
  subtitle: {
    fontSize: 16,
    color: "#555",
    marginTop: 10,
  },
});
