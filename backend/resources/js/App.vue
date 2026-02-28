<template>
  <div id="app">
    <nav class="navbar">
      <div class="nav-brand">
        <router-link to="/">SubTerra</router-link>
      </div>
      <div class="nav-links">
        <router-link to="/" class="nav-link">Jobs</router-link>
        <router-link to="/new" class="nav-link">Neue Simulation</router-link>
      </div>
    </nav>
    <main class="container">
      <router-view />
    </main>
  </div>
</template>

<script>
export default {
  name: 'App',
};
</script>
