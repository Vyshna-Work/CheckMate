// React + state hooks
import React, { useState, useEffect } from 'react';

// Basic React Native UI components
import { 
  View, 
  Text, 
  TextInput, 
  TouchableOpacity, 
  StyleSheet, 
  Alert 
} from 'react-native';

// Navigation types
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RootStackParamList } from './App';

// eye icon
import Icon from 'react-native-vector-icons/MaterialIcons';

// device id
import DeviceInfo from 'react-native-device-info';

// Navigation type for this screen
type RegisterScreenNavigationProp = NativeStackNavigationProp<
  RootStackParamList,
  'Register'
>;

export default function RegisterScreen({
  navigation,
}: {
  navigation: RegisterScreenNavigationProp;
}) {

  // Local state
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [birthday, setBirthday] = useState('');
  const [deviceId, setDeviceId] = useState("");

  useEffect(() => {
  DeviceInfo.getUniqueId().then(id => {
    setDeviceId(id);
  });
}, []);

  // Register function
  const handleRegister = async () => {

    if (password.length < 8) {
      Alert.alert("Password too short!", "Password must be at least 8 characters");
      return;
    }

    if (password !== confirm) {
      Alert.alert("Passwords do not match!", "Make sure both passwords are the same");
      return;
    }
    // birthday validation
    const birthdayRegex = /^\d{4}-\d{2}-\d{2}$/;

    if (!birthdayRegex.test(birthday)) {
      Alert.alert("Invalid Birthday", "Birthday must be in YYYY-MM-DD format");
      return;
    }
    
    const birthDate = new Date(birthday);
    const today = new Date();

    let age = today.getFullYear() - birthDate.getFullYear();
    const monthDiff = today.getMonth() - birthDate.getMonth();

    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
      age--;
    }

    if (age < 10) {
      Alert.alert("Too Young", "You must be at least 10 years old to register.");
      return;
    }

    try {
      const response = await fetch("http://172.20.10.5:5000/users/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name,
          password: password,
          birthday: birthday,
          device_id: deviceId
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        Alert.alert("Registration Failed", errorData.error || "Unknown error");
        return;
      }

      Alert.alert("Success", "Account created!");
      navigation.navigate("SignIn");

    } catch (error) {
      Alert.alert("Network Error", "Could not reach the server.");
      console.log("Registration error:", error);
    }
  };

  return (
    <View style={styles.container}>

      {/* Back button */}
      <TouchableOpacity style={styles.backButton} onPress={() => navigation.goBack()}>
        <Text style={styles.backText}>Back</Text>
      </TouchableOpacity>

      {/* Title */}
      <Text style={styles.title}>Create Account</Text>

      {/* Name input */}
      <TextInput
        style={styles.input}
        placeholder="Full Name"
        placeholderTextColor="#888"
        value={name}
        onChangeText={setName}
      />
      {/* birthday input */}
      <TextInput
        style={styles.input}
        placeholder="Birthday (YYYY-MM-DD)"
        value={birthday}
        onChangeText={setBirthday}
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

      {/* Confirm Password input with eye icon */}
      <View style={styles.passwordContainer}>
        <TextInput
          style={styles.passwordInput}
          placeholder="Confirm Password"
          placeholderTextColor="#888"
          value={confirm}
          onChangeText={setConfirm}
          secureTextEntry={!showConfirm}
        />
        <TouchableOpacity onPress={() => setShowConfirm(!showConfirm)}>
          <Icon 
            name={showConfirm ? "visibility-off" : "visibility"} 
            size={24} 
            color="#555" 
          />
        </TouchableOpacity>
      </View>

      {/* Register button */}
      <TouchableOpacity style={styles.button} onPress={handleRegister}>
        <Text style={styles.buttonText}>Register</Text>
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
    backgroundColor: 'white'
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
  },

  passwordInput: {
    flex: 1,
    padding: 15,
    fontSize: 16,
    color: 'black',
  },

  button: {
    backgroundColor: '#007bff',
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

  backButton: {
    marginBottom: 20,
  },

  backText: {
    fontSize: 18,
    color: '#007bff',
  },
});
