// This file contains the migration script for the TollManagement contract
const TollManagement = artifacts.require("TollManagement");

module.exports = function (deployer) {
  deployer.deploy(TollManagement);
};