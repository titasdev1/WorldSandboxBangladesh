// Merge the CC0 Quaternius Standard skeleton with its in-place animation libraries.
// Source assets: https://quaternius.itch.io/universal-base-characters
// https://quaternius.itch.io/universal-animation-library
// https://quaternius.itch.io/universal-animation-library-2
// Uses glTF Transform's documented NodeIO/Animation APIs; the output retains the
// character skin, textures and bone names and copies compatible animation tracks.
import { NodeIO } from '@gltf-transform/core';
import { KHRONOS_EXTENSIONS } from '@gltf-transform/extensions';
import fs from 'node:fs/promises';

const io = new NodeIO().registerExtensions(KHRONOS_EXTENSIONS);

function copyAccessor(targetDocument, sourceAccessor) {
  const sourceArray = sourceAccessor.getArray();
  const copy = targetDocument.createAccessor()
    .setType(sourceAccessor.getType())
    .setNormalized(sourceAccessor.getNormalized());
  if (sourceArray) copy.setArray(sourceArray.slice());
  return copy;
}

async function mergeAnimations(characterPath, outputPath, reportPath, animationPaths) {
  const character = await io.read(characterPath);
  const root = character.getRoot();
  const characterNodes = new Map();
  for (const node of root.listNodes()) {
    if (node.getName()) characterNodes.set(node.getName(), node);
  }
  if (characterNodes.size < 10) throw new Error('Character GLTF has too few named nodes to be a rigged human.');

  const unmatchedNodes = new Set();
  const sourceClipNames = [];
  for (const animationPath of animationPaths) {
    const animationDocument = await io.read(animationPath);
    const nodeMap = new Map();
    for (const node of animationDocument.getRoot().listNodes()) {
      const name = node.getName();
      if (!name) continue;
      const destination = characterNodes.get(name);
      if (destination) nodeMap.set(node, destination);
      else unmatchedNodes.add(name);
    }
    if (nodeMap.size < 30) {
      throw new Error(`Animation rig match is too small for ${animationPath}: matched ${nodeMap.size} nodes.`);
    }
    for (const sourceAnimation of animationDocument.getRoot().listAnimations()) {
      let name = sourceAnimation.getName() || `Animation_${sourceClipNames.length + 1}`;
      if (sourceClipNames.includes(name)) {
        let suffix = 2;
        while (sourceClipNames.includes(`${name}_${suffix}`)) suffix++;
        name = `${name}_${suffix}`;
      }
      const destinationAnimation = character.createAnimation(name);
      for (const sourceChannel of sourceAnimation.listChannels()) {
        const targetNode = nodeMap.get(sourceChannel.getTargetNode());
        const sourceSampler = sourceChannel.getSampler();
        if (!targetNode || !sourceSampler) continue;
        const sourceInput = sourceSampler.getInput();
        const sourceOutput = sourceSampler.getOutput();
        if (!sourceInput || !sourceOutput) continue;
        const sampler = character.createAnimationSampler()
          .setInput(copyAccessor(character, sourceInput))
          .setOutput(copyAccessor(character, sourceOutput))
          .setInterpolation(sourceSampler.getInterpolation());
        destinationAnimation.addSampler(sampler).addChannel(
          character.createAnimationChannel()
            .setTargetNode(targetNode)
            .setTargetPath(sourceChannel.getTargetPath())
            .setSampler(sampler)
        );
      }
      if (destinationAnimation.listChannels().length > 0) sourceClipNames.push(name);
      else root.listAnimations().filter(animation => animation === destinationAnimation);
    }
    console.log(`Merged ${sourceAnimationCount(animationDocument)} compatible clips from ${animationPath}`);
  }

  if (sourceClipNames.length < 30) {
    throw new Error(`Merged animation count unexpectedly low: ${sourceClipNames.length}.`);
  }
  const binary = await io.writeBinary(character);
  await fs.writeFile(outputPath, binary);
  const report = {
    character_source: characterPath,
    animation_sources: animationPaths,
    character_named_node_count: characterNodes.size,
    animation_clip_count: sourceClipNames.length,
    animation_names: sourceClipNames,
    unmatched_source_node_names: [...unmatchedNodes].sort(),
    output_bytes: binary.byteLength,
  };
  await fs.writeFile(reportPath, JSON.stringify(report, null, 2) + '\n');
  console.log(`Merged ${sourceClipNames.length} clips into ${outputPath} (${(binary.byteLength / 1048576).toFixed(2)} MiB).`);
}

function sourceAnimationCount(document) {
  return document.getRoot().listAnimations().length;
}

const [, , characterPath, outputPath, reportPath, ...animationPaths] = process.argv;
if (!characterPath || !outputPath || !reportPath || animationPaths.length < 1) {
  console.error('Usage: node merge_quaternius_character.mjs <character.gltf> <output.glb> <report.json> <animation-library.glb> [...]');
  process.exit(2);
}

mergeAnimations(characterPath, outputPath, reportPath, animationPaths).catch(error => {
  console.error('Quaternius hero merge failed:', error);
  process.exit(1);
});
