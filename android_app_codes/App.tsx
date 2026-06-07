/**
 * Main app entry — sets up navigation and the landing screen
 */

import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { StatusBar, StyleSheet, useColorScheme, View, Text, Image, TouchableOpacity } from 'react-native';
import {
  SafeAreaProvider,
  useSafeAreaInsets,
} from 'react-native-safe-area-context';

import RegisterScreen from './RegisterScreen';
import SignInScreen from './SignInScreen';
import HomeScreen from './HomeScreen';

import type { NativeStackNavigationProp } from '@react-navigation/native-stack';

// All screens in the app go here
export type RootStackParamList = {
  Landing: undefined;
  Register: undefined;
  SignIn: undefined;
  Home: undefined; 
};

// Creates the navigation stack (like pages in a book)
const Stack = createNativeStackNavigator();

function App() {
  const isDarkMode = useColorScheme() === 'dark';

  return (
    // Wraps the whole app with navigation support
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {/* First screen the user sees */}
        <Stack.Screen name="Landing" component={AppContent} />

        {/* Registration page */}
        <Stack.Screen name="Register" component={RegisterScreen} />

        {/* SignIn Page */}
        <Stack.Screen name= "SignIn" component={SignInScreen} />

        {/* SignIn Page */}
        <Stack.Screen name="Home" component={HomeScreen} />

      </Stack.Navigator>
    </NavigationContainer>
  );
}

// Type for navigation so TS stops complaining
type LandingScreenNavigationProp = NativeStackNavigationProp<
  RootStackParamList,
  'Landing'
>;

function AppContent({ navigation }: { navigation: LandingScreenNavigationProp }) {
  const safeAreaInsets = useSafeAreaInsets();

  return (
    <View style={styles.container}>
      {/* App logo */}
      <Image
        source={{ uri: 'https://via.placeholder.com/150' }}
        style={styles.logo}
      />

      {/* Button that takes user to registration page */}
      <TouchableOpacity
        style={styles.button}
        onPress={() => navigation.navigate('Register')}
      >
        <Text style={styles.buttonText}>Register</Text>
      </TouchableOpacity>

      {/* Sign in button */}
      <TouchableOpacity style={styles.buttonSecondary}
        onPress={() => navigation.navigate('SignIn')}
      >
        <Text style={styles.buttonText}>Sign In</Text>
      </TouchableOpacity>
    </View>
  );
}

// Basic styling for the landing page
const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'white',
  },

  logo: {
    width: 150,
    height: 150,
    marginBottom: 40,
  },

  button: {
    width: '80%',
    padding: 15,
    backgroundColor: '#007bff',
    borderRadius: 10,
    alignItems: 'center',
    marginBottom: 20,
  },

  buttonSecondary: {
    width: '80%',
    padding: 15,
    backgroundColor: '#28a745',
    borderRadius: 10,
    alignItems: 'center',
  },

  buttonText: {
    color: 'white',
    fontSize: 18,
    fontWeight: 'bold',
  },
});

export default App;
