const { createApp, ref } = Vue

createApp({
  setup(){
    const song = ref(null)
    const output = ref(null)
    const status = ref("")

    async function selectSong(){
      song.value = await window.api.selectFile()
    }

    async function selectOutput(){
      output.value = await window.api.selectOutput()
    }

    async function split(){
      if(!song.value || !output.value){
        alert("Select song and output")
        return
      }
      status.value = "Separating..."
      try {
        await window.api.runDemucs(song.value, output.value)
        status.value = "Done!"
      } catch (error) {
        console.error(error)
        status.value = "Error: " + error.message
        alert("Error: " + error.message)
      }
    }

    return { song, output, status, selectSong, selectOutput, split }
  },
  template: `
  <div>
    <h1>BLOND Stem Splitter</h1>
    <button @click="selectSong">Select Song</button>
    <p>{{song}}</p>
    <button @click="selectOutput">Select Output Folder</button>
    <p>{{output}}</p>
    <button @click="split">Split</button>
    <p>{{status}}</p>
  </div>
  `
}).mount("#app")