// React + state hooks
import React, { useState, useEffect } from 'react';

// Basic UI components from React Native
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert } from 'react-native';

// Save user data after login
import AsyncStorage from '@react-native-async-storage/async-storage';

// Navigation types
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RootStackParamList } from './App';

import Icon from 'react-native-vector-icons/MaterialIcons';
import DeviceInfo from 'react-native-device-info';

// Navigation type for this screen
type SignInScreenNavigationProp = NativeStackNavigationProp<
  RootStackParamList,
  'SignIn'
>;

export default function SignInScreen({
  navigation,
}: {
  navigation: SignInScreenNavigationProp;
}) {

  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [deviceId, setDeviceId] = useState("");

  useEffect(() => {
  DeviceInfo.getUniqueId().then(id => {
    setDeviceId(id);
  });
}, []);

  const handleSignIn = async () => {

    if (!name || !password) {
      Alert.alert("Missing fields", "Please enter both name and password");
      return;
    }

    if (password.length < 8) {
      Alert.alert("Invalid password", "Password must be at least 8 characters");
      return;
    }

    try {
      const response = await fetch("http://172.20.10.5:5000/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, password, device_id: deviceId }),
      });

      const data = await response.json();

      if (response.status === 200) {
        Alert.alert("Success", "Signed in!");

        await AsyncStorage.setItem("user_id", data.user_id.toString());
        await AsyncStorage.setItem("ble_id", data.ble_id);
        await AsyncStorage.setItem("name", data.name);

        navigation.navigate("Home");

      } else {
        Alert.alert("Error", data.error || "Login failed");
      }

    } catch (error) {
      Alert.alert("Network Error", "Could not connect to server");
    }
  };

  return (
    <View style={styles.container}>

      {/* Back button */}
      <TouchableOpacity style={styles.backButton} onPress={() => navigation.goBack()}>
        <Text style={styles.backText}>Back</Text>
      </TouchableOpacity>

      {/* Title */}
      <Text style={styles.title}>Sign In</Text>

      {/* Name input */}
      <TextInput
        style={styles.input}
        placeholder="Full Name"
        placeholderTextColor="#888"
        value={name}
        onChangeText={setName}
      />

      {/* Password input with eye icon */}
      <View style={styles.passwordContainer}>
        <TextInput
          style={styles.passwordInput}
          placeholder="Password"
          placeholderTextColor="#888"
          value={password}
          onChangeText={setPassword}
          secureTextEntry={!showPassword}
        />
        <TouchableOpacity onPress={() => setShowPassword(!showPassword)}>
          <Icon 
            name={showPassword ? "visibility-off" : "visibility"} 
            size={24} 
            color="#555" 
          />
        </TouchableOpacity>
      </View>

      {/* Sign In button */}
      <TouchableOpacity style={styles.button} onPress={handleSignIn}>
        <Text style={styles.buttonText}>Sign In</Text>
      </TouchableOpacity>

    </View>
  );
}

// Styles
const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: 30,
    backgroundColor: 'white',
  },

  backButton: {
    marginBottom: 20,
  },

  backText: {
    fontSize: 18,
    color: '#007bff',
  },

  title: {
    fontSize: 28,
    fontWeight: 'bold',
    marginBottom: 40,
    textAlign: 'center',
  },

  input: {
    width: '100%',
    padding: 15,
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 10,
    marginBottom: 20,
    fontSize: 16,
    color: 'black',
    backgroundColor: 'white',
  },

  passwordContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 10,
    paddingHorizontal: 10,
    marginBottom: 20,
    backgroundColor: 'white',
    height: 55, // keeps icon centered
  },

  passwordInput: {
    flex: 1,
    fontSize: 16,
    color: 'black',
    paddingVertical: 10,
  },

  button: {
    backgroundColor: '#28a745',
    padding: 15,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 10,
  },

  buttonText: {
    color: 'white',
    fontSize: 18,
    fontWeight: 'bold',
  },
});
